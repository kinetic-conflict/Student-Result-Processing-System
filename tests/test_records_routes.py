import mysql.connector
import pytest

from db import execute_query
from tests.factories import (make_exam, make_faculty, make_legacy_mark, make_student, make_subject,
                             make_user, record_mark)
from tests.helpers import post


@pytest.fixture
def admin(sign_in):
    return sign_in('admin')


def rows(app, sql, params=()):
    with app.app_context():
        return execute_query(sql, params)


STUDENT_FORM = {'registration_number': 'S100', 'full_name': 'Asha Menon', 'email': 'asha@example.test',
                'department': 'Computer Science', 'semester': '3', 'academic_year': '2024-2025'}


# ---- students ---------------------------------------------------------------

def test_adding_a_student_saves_it_and_is_audited(app, admin):
    response = post(admin.client, '/students/add', STUDENT_FORM)
    assert response.status_code == 302
    (row,) = rows(app, 'SELECT * FROM students')
    assert (row['registration_number'], row['full_name'], row['semester']) == ('S100', 'Asha Menon', 3)
    assert rows(app, 'SELECT action FROM audit_log')[0]['action'] == 'student.create'


def test_a_duplicate_registration_number_is_explained_and_the_form_keeps_its_values(app, admin):
    post(admin.client, '/students/add', STUDENT_FORM)
    response = post(admin.client, '/students/add', dict(STUDENT_FORM, full_name='Someone Else'))
    assert response.status_code == 200
    assert b'already exists' in response.data
    assert b'Someone Else' in response.data
    assert len(rows(app, 'SELECT 1 FROM students')) == 1


@pytest.mark.parametrize('field, value, message', [
    ('registration_number', '', b'Registration number is required'),
    ('registration_number', 'X' * 21, b'at most 20'),
    ('full_name', '   ', b'Full name is required'),
    ('email', 'not-an-email', b'valid email'),
    ('semester', 'abc', b'whole number'),
    ('semester', '0', b'at least 1'),
    ('semester', '11', b'at most 10'),
    ('academic_year', '2024-2026', b'YYYY-YYYY'),
])
def test_student_form_validation(app, admin, field, value, message):
    response = post(admin.client, '/students/add', dict(STUDENT_FORM, **{field: value}))
    assert response.status_code == 200
    assert message in response.data
    assert rows(app, 'SELECT 1 FROM students') == []


def test_editing_a_student(app, admin):
    with app.app_context():
        student = make_student('S100', 'Old Name')
    assert admin.client.get(f'/students/{student}/edit').status_code == 200
    response = post(admin.client, f'/students/{student}/edit', dict(STUDENT_FORM, full_name='New Name'))
    assert response.status_code == 302
    assert rows(app, 'SELECT full_name FROM students')[0]['full_name'] == 'New Name'
    bad = post(admin.client, f'/students/{student}/edit', dict(STUDENT_FORM, semester='99'))
    assert bad.status_code == 200 and b'at most 10' in bad.data


def test_deleting_a_student_removes_them_and_their_marks(app, admin):
    with app.app_context():
        student, subject = make_student(), make_subject()
        record_mark(student, subject, 'CAT1', 40)
    assert post(admin.client, f'/students/{student}/delete').status_code == 302
    assert rows(app, 'SELECT 1 FROM students') == []
    assert rows(app, 'SELECT 1 FROM assessment_marks') == []


def test_a_student_with_a_login_account_cannot_be_deleted(app, admin):
    with app.app_context():
        student = make_student()
        make_user('stu1', 'student', student_id=student)
    response = post(admin.client, f'/students/{student}/delete', follow_redirects=True)
    assert b'login account' in response.data
    assert len(rows(app, 'SELECT 1 FROM students')) == 1


def test_student_list_searches_literally_and_pages(app, admin):
    with app.app_context():
        for index in range(30):
            make_student(f'R{index:03}', f'Name {index:02}')
    first = admin.client.get('/students').data
    assert b'R000' in first and b'R029' not in first
    assert b'R029' in admin.client.get('/students?page=2').data
    assert b'R007' in admin.client.get('/students?search=R007').data
    assert b'R008' not in admin.client.get('/students?search=R007').data
    assert b'R000' not in admin.client.get('/students?search=%25').data     # '%' is literal
    assert admin.client.get('/students?page=junk').status_code == 200


def test_student_page_shows_legacy_marks_with_grades(app, admin):
    with app.app_context():
        student, subject, exam = make_student(), make_subject(), make_exam()
        make_legacy_mark(student, subject, exam, 85, 100)
    page = admin.client.get(f'/students/{student}').data
    assert b'Mid Term' in page and b'85' in page


def test_unknown_student_redirects_with_a_message(admin):
    response = admin.client.get('/students/99999', follow_redirects=True)
    assert b'not found' in response.data


def test_unexpected_database_errors_never_reach_the_page(app, admin, monkeypatch):
    def explode(*args, **kwargs):
        raise mysql.connector.Error(msg="Table 'secret_schema.hidden' doesn't exist", errno=1146)
    monkeypatch.setattr('routes.students.execute_update', explode)
    response = post(admin.client, '/students/add', STUDENT_FORM)
    assert response.status_code == 200
    assert b'could not be saved' in response.data
    assert b'secret_schema' not in response.data


# ---- subjects ---------------------------------------------------------------

SUBJECT_FORM = {'subject_code': 'CS301', 'subject_name': 'Algorithms', 'credits': '4', 'semester': '3'}


def test_subject_crud_round_trip(app, admin):
    assert post(admin.client, '/subjects/add', SUBJECT_FORM).status_code == 302
    (subject,) = rows(app, 'SELECT * FROM subjects')
    assert float(subject['credits']) == 4.0
    response = post(admin.client, f"/subjects/{subject['subject_id']}/edit",
                    dict(SUBJECT_FORM, subject_name='Renamed', credits='3.5'))
    assert response.status_code == 302
    assert rows(app, 'SELECT subject_name FROM subjects')[0]['subject_name'] == 'Renamed'
    assert post(admin.client, f"/subjects/{subject['subject_id']}/delete").status_code == 302
    assert rows(app, 'SELECT 1 FROM subjects') == []


def test_duplicate_subject_code(app, admin):
    post(admin.client, '/subjects/add', SUBJECT_FORM)
    response = post(admin.client, '/subjects/add', SUBJECT_FORM)
    assert response.status_code == 200 and b'already exists' in response.data


@pytest.mark.parametrize('field, value, message', [
    ('subject_code', '', b'Subject code is required'),
    ('credits', '0', b'at least 0.1'),
    ('credits', '10.5', b'at most 10'),
    ('credits', 'abc', b'must be a number'),
    ('credits', '2.55', b'decimal place'),
    ('semester', '11', b'at most 10'),
])
def test_subject_validation(app, admin, field, value, message):
    response = post(admin.client, '/subjects/add', dict(SUBJECT_FORM, **{field: value}))
    assert response.status_code == 200 and message in response.data
    assert rows(app, 'SELECT 1 FROM subjects') == []


def test_a_subject_with_any_marks_cannot_be_deleted(app, admin):
    with app.app_context():
        legacy, weighted = make_subject('A1'), make_subject('B1')
        student, exam = make_student(), make_exam()
        make_legacy_mark(student, legacy, exam)
        record_mark(student, weighted, 'CAT1', 30)
    for subject in (legacy, weighted):
        response = post(admin.client, f'/subjects/{subject}/delete', follow_redirects=True)
        assert b'has marks' in response.data
    assert len(rows(app, 'SELECT 1 FROM subjects')) == 2
    assert len(rows(app, 'SELECT 1 FROM assessment_marks')) == 1


def test_a_subject_with_assigned_faculty_can_still_be_deleted_and_the_assignment_goes(app, admin):
    from tests.factories import assign
    with app.app_context():
        subject, faculty = make_subject(), make_faculty()
        assign(faculty, subject)
    assert post(admin.client, f'/subjects/{subject}/delete').status_code == 302
    assert rows(app, 'SELECT 1 FROM faculty_assignments') == []


# ---- examinations -----------------------------------------------------------

EXAM_FORM = {'exam_name': 'Mid Term', 'academic_year': '2024-2025', 'semester': '3',
             'exam_date': '2024-10-15'}


def test_examination_crud_and_results_page(app, admin):
    assert post(admin.client, '/examinations/add', EXAM_FORM).status_code == 302
    assert post(admin.client, '/examinations/add', dict(EXAM_FORM, exam_name='No Date', exam_date='')).status_code == 302
    exam = rows(app, "SELECT exam_id FROM examinations WHERE exam_name = 'Mid Term'")[0]['exam_id']
    assert post(admin.client, f'/examinations/{exam}/edit', dict(EXAM_FORM, exam_name='Renamed')).status_code == 302
    page = admin.client.get(f'/examinations/{exam}/results')
    assert page.status_code == 200 and b'Renamed' in page.data


@pytest.mark.parametrize('field, value, message', [
    ('exam_name', '', b'Examination name is required'),
    ('academic_year', '2024', b'YYYY-YYYY'),
    ('semester', 'x', b'whole number'),
    ('exam_date', '15/10/2024', b'YYYY-MM-DD'),
])
def test_examination_validation(app, admin, field, value, message):
    response = post(admin.client, '/examinations/add', dict(EXAM_FORM, **{field: value}))
    assert response.status_code == 200 and message in response.data
    assert rows(app, 'SELECT 1 FROM examinations') == []


def test_unknown_examination_redirects_with_a_message(admin):
    assert b'not found' in admin.client.get('/examinations/9999/results', follow_redirects=True).data
