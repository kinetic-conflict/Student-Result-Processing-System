import pytest

from db import execute_query
from services import auth_service, faculty_service
from services.validation import ValidationError
from tests.factories import PASSWORD, assign, make_faculty, make_subject, make_user
from tests.helpers import login, post

FACULTY_FORM = {'employee_id': 'F100', 'full_name': 'Dr Rao', 'email': 'rao@example.test',
                'department': 'Computer Science'}


@pytest.fixture
def admin(sign_in):
    return sign_in('admin')


def rows(app, sql, params=()):
    with app.app_context():
        return execute_query(sql, params)


# ---- faculty records --------------------------------------------------------

def test_creating_and_editing_a_faculty_member(app, admin):
    assert post(admin.client, '/admin/faculty/new', FACULTY_FORM).status_code == 302
    (row,) = rows(app, 'SELECT * FROM faculty')
    assert (row['employee_id'], row['full_name'], row['is_active']) == ('F100', 'Dr Rao', 1)
    assert admin.client.get(f"/admin/faculty/{row['faculty_id']}/edit").status_code == 200
    assert post(admin.client, f"/admin/faculty/{row['faculty_id']}/edit",
                dict(FACULTY_FORM, full_name='Dr R. Rao')).status_code == 302
    assert rows(app, 'SELECT full_name FROM faculty')[0]['full_name'] == 'Dr R. Rao'


@pytest.mark.parametrize('field, value, message', [
    ('employee_id', '', b'Employee ID is required'),
    ('full_name', '', b'Full name is required'),
    ('email', 'nope', b'valid email'),
    ('employee_id', 'X' * 21, b'at most 20'),
])
def test_faculty_validation(app, admin, field, value, message):
    response = post(admin.client, '/admin/faculty/new', dict(FACULTY_FORM, **{field: value}))
    assert response.status_code == 200 and message in response.data
    assert rows(app, 'SELECT 1 FROM faculty') == []


def test_duplicate_employee_ids_and_emails_are_explained(app, admin):
    post(admin.client, '/admin/faculty/new', FACULTY_FORM)
    same_id = post(admin.client, '/admin/faculty/new', dict(FACULTY_FORM, email='other@example.test'))
    same_email = post(admin.client, '/admin/faculty/new', dict(FACULTY_FORM, employee_id='F200'))
    assert b'already exists' in same_id.data and b'already exists' in same_email.data
    assert len(rows(app, 'SELECT 1 FROM faculty')) == 1


def test_the_list_shows_assignment_counts_and_pages(app, admin):
    with app.app_context():
        faculty, subject = make_faculty('F1', 'Prof One'), make_subject()
        assign(faculty, subject)
    page = admin.client.get('/admin/faculty').data
    assert b'Prof One' in page and b'F1' in page
    assert admin.client.get('/admin/faculty?search=zzz&page=junk').status_code == 200


# ---- assignments ------------------------------------------------------------

def test_assigning_and_removing_subjects(app, admin):
    with app.app_context():
        faculty, first, second = make_faculty(), make_subject('A1'), make_subject('B1')
    page = admin.client.get(f'/admin/faculty/{faculty}/assignments').data
    assert b'A1' in page and b'B1' in page
    assert post(admin.client, f'/admin/faculty/{faculty}/assignments/add',
                {'subject_id': str(first)}).status_code == 302
    assigned = rows(app, 'SELECT * FROM faculty_assignments')
    assert [r['subject_id'] for r in assigned] == [first]
    offered = admin.client.get(f'/admin/faculty/{faculty}/assignments').data
    assert offered.count(b'B1') >= 1
    assert post(admin.client,
                f"/admin/faculty/{faculty}/assignments/{assigned[0]['assignment_id']}/remove").status_code == 302
    assert rows(app, 'SELECT 1 FROM faculty_assignments') == []
    assert {'faculty.assign', 'faculty.unassign'} <= {r['action'] for r in rows(app, 'SELECT action FROM audit_log')}


def test_assignment_mistakes_are_reported_not_crashed(app, admin):
    with app.app_context():
        faculty, subject = make_faculty(), make_subject()
        assign(faculty, subject)
    duplicate = post(admin.client, f'/admin/faculty/{faculty}/assignments/add',
                     {'subject_id': str(subject)}, follow_redirects=True)
    assert b'already assigned' in duplicate.data
    unknown = post(admin.client, f'/admin/faculty/{faculty}/assignments/add',
                   {'subject_id': '99999'}, follow_redirects=True)
    assert b'does not exist' in unknown.data
    junk = post(admin.client, f'/admin/faculty/{faculty}/assignments/add',
                {'subject_id': 'abc'}, follow_redirects=True)
    assert junk.status_code == 200
    assert post(admin.client, '/admin/faculty/99999/assignments/add', {'subject_id': '1'}).status_code == 404


def test_removing_an_assignment_of_another_faculty_member_is_refused(app, admin):
    with app.app_context():
        one, two, subject = make_faculty('F1'), make_faculty('F2'), make_subject()
        assignment = assign(two, subject)
    response = post(admin.client, f'/admin/faculty/{one}/assignments/{assignment}/remove')
    assert response.status_code == 404
    assert len(rows(app, 'SELECT 1 FROM faculty_assignments')) == 1


def test_a_new_assignment_reaches_the_faculty_members_dashboard(app, admin, sign_in):
    with app.app_context():
        faculty, subject = make_faculty('F9', 'Dr Nine'), make_subject('ZZ900', 'Zebra Studies')
    teacher = sign_in('faculty', faculty_id=faculty)
    assert b'ZZ900' not in teacher.client.get('/faculty').data
    post(admin.client, f'/admin/faculty/{faculty}/assignments/add', {'subject_id': str(subject)})
    assert b'ZZ900' in teacher.client.get('/faculty').data


# ---- deactivation -----------------------------------------------------------

def test_deactivating_faculty_also_locks_their_account_and_ends_sessions(app, admin, sign_in):
    with app.app_context():
        faculty = make_faculty('F9', 'Dr Nine')
        subject = make_subject()
        assign(faculty, subject)
    teacher = sign_in('faculty', faculty_id=faculty)
    assert teacher.client.get('/faculty').status_code == 200

    assert post(admin.client, f'/admin/faculty/{faculty}/deactivate').status_code == 302
    assert rows(app, 'SELECT is_active FROM faculty')[0]['is_active'] == 0
    assert teacher.client.get('/faculty').status_code == 302               # session ended
    assert login(app.test_client(), teacher.username).status_code == 200   # cannot sign back in

    assert post(admin.client, f'/admin/faculty/{faculty}/activate').status_code == 302
    assert login(app.test_client(), teacher.username).status_code == 302


def test_service_level_activation_without_an_account(ctx):
    faculty = make_faculty()
    faculty_service.set_active(faculty, False)
    assert execute_query('SELECT is_active FROM faculty')[0]['is_active'] == 0


def test_assign_subject_service_rules(ctx):
    faculty, subject = make_faculty(), make_subject()
    faculty_service.assign_subject(faculty, subject)
    with pytest.raises(ValidationError, match='already assigned'):
        faculty_service.assign_subject(faculty, subject)
    with pytest.raises(ValidationError, match='does not exist'):
        faculty_service.assign_subject(faculty, 9999)
    with pytest.raises(ValidationError, match='does not exist'):
        faculty_service.assign_subject(9999, subject)
