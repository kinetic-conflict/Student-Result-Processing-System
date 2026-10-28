import re

import pytest

from db import execute_query
from services import auth_service
from services.validation import ValidationError
from tests.factories import PASSWORD, make_faculty, make_student, make_user
from tests.helpers import login, post


@pytest.fixture
def admin(sign_in):
    return sign_in('admin')


def users(app, where='1 = 1', params=()):
    with app.app_context():
        return execute_query(f'SELECT * FROM users WHERE {where} ORDER BY user_id', params)


def audit_text(app):
    with app.app_context():
        return ' '.join(f"{r['action']} {r['detail'] or ''}" for r in execute_query('SELECT * FROM audit_log'))


def shown_password(response):
    """The one-time temporary password on a credentials page."""
    match = re.search(rb'<code[^>]*id="temporary-password"[^>]*>([^<]+)</code>', response.data)
    assert match, 'no temporary password shown'
    return match.group(1).decode()


# ---- creating accounts ------------------------------------------------------

def test_admin_creates_a_faculty_account_and_sees_the_temporary_password_once(app, admin):
    with app.app_context():
        faculty = make_faculty('F100', 'Dr Rao')
    response = post(admin.client, '/admin/users/new',
                    {'username': 'drrao', 'email': 'rao@example.test', 'role': 'faculty',
                     'faculty_id': str(faculty)})
    assert response.status_code == 200
    temporary = shown_password(response)
    assert b'drrao' in response.data and b'change it' in response.data.lower()

    (row,) = users(app, "username = 'drrao'")
    assert row['role'] == 'faculty' and row['faculty_id'] == faculty and row['must_change_password'] == 1
    assert temporary not in row['password_hash']

    newcomer = app.test_client()
    landing = login(newcomer, 'drrao', temporary)
    assert landing.headers['Location'].endswith('/account/password')   # forced change first


def test_the_temporary_password_is_not_logged_flashed_or_audited(app, admin):
    with app.app_context():
        student = make_student('S100', 'Asha')
    response = post(admin.client, '/admin/users/new',
                    {'username': 'asha', 'role': 'student', 'student_id': str(student)})
    temporary = shown_password(response)
    assert temporary not in audit_text(app)
    with admin.client.session_transaction() as session:
        assert temporary not in str(dict(session))
    assert 'no-store' in response.headers['Cache-Control']
    assert temporary.encode() not in admin.client.get('/admin/users').data


@pytest.mark.parametrize('form, message', [
    ({'username': 'ab', 'role': 'admin'}, b'Username must be'),
    ({'username': 'newadmin', 'role': 'superuser'}, b'valid role'),
    ({'username': 'newadmin', 'role': 'student'}, b'linked to a student record'),
    ({'username': 'newadmin', 'role': 'faculty', 'faculty_id': '9999'}, b'does not exist'),
    ({'username': 'newadmin', 'role': 'admin', 'email': 'bad'}, b'valid email'),
])
def test_account_creation_validation(app, admin, form, message):
    response = post(admin.client, '/admin/users/new', form)
    assert response.status_code == 200 and message in response.data
    assert users(app, "username = 'newadmin'") == []


def test_a_student_record_gets_only_one_account(app, admin):
    with app.app_context():
        student = make_student('S100', 'Asha')
        make_user('asha', 'student', student_id=student)
    response = post(admin.client, '/admin/users/new',
                    {'username': 'asha2', 'role': 'student', 'student_id': str(student)})
    assert b'already has an account' in response.data


def test_only_records_without_an_account_are_offered(app, admin):
    with app.app_context():
        taken, free = make_student('S100', 'Has Account'), make_student('S101', 'No Account')
        make_user('hasacc', 'student', student_id=taken)
    page = admin.client.get('/admin/users/new').data
    assert b'S101' in page and b'S100' not in page


def test_admin_accounts_can_be_created_too(app, admin):
    response = post(admin.client, '/admin/users/new', {'username': 'second', 'role': 'admin'})
    assert response.status_code == 200
    assert users(app, "username = 'second'")[0]['role'] == 'admin'


# ---- bulk creation ----------------------------------------------------------

def test_accounts_can_be_created_for_every_student_without_one(app, admin):
    with app.app_context():
        for index in range(3):
            make_student(f'B{index:03}', f'Bulk {index}')
        existing = make_student('HAS1', 'Has One')
        make_user('has1', 'student', student_id=existing)
    response = post(admin.client, '/admin/users/bulk', {'role': 'student'})
    assert response.status_code == 200
    assert len(users(app, "role = 'student'")) == 4
    passwords = re.findall(rb'class="bulk-password">([^<]+)<', response.data)
    assert len(passwords) == 3 and len(set(passwords)) == 3
    assert all(row['must_change_password'] == 1 for row in users(app, "username LIKE 'b0%'"))
    again = post(admin.client, '/admin/users/bulk', {'role': 'student'})
    assert b'Nobody needs an account' in again.data


def test_bulk_creation_reports_records_it_had_to_skip(app, admin):
    with app.app_context():
        make_student('OK001', 'Fine')
        make_student('BAD 1', 'Spaces not allowed in usernames')
    response = post(admin.client, '/admin/users/bulk', {'role': 'student'})
    assert b'ok001' in response.data and b'BAD 1' in response.data
    assert len(users(app, "role = 'student'")) == 1


def test_bulk_creation_only_works_for_student_and_faculty_roles(admin):
    assert post(admin.client, '/admin/users/bulk', {'role': 'admin'}).status_code == 400


# ---- editing, status, resetting ---------------------------------------------

def test_editing_the_username_and_email(app, admin):
    with app.app_context():
        user_id = make_user('olduser', 'admin')
    assert admin.client.get(f'/admin/users/{user_id}/edit').status_code == 200
    assert post(admin.client, f'/admin/users/{user_id}/edit',
                {'username': 'newuser', 'email': 'new@example.test'}).status_code == 302
    row = users(app, 'user_id = %s', (user_id,))[0]
    assert (row['username'], row['email'], row['role']) == ('newuser', 'new@example.test', 'admin')


def test_editing_cannot_take_another_accounts_username_or_change_the_role(app, admin):
    with app.app_context():
        make_user('taken', 'admin')
        user_id = make_user('mine', 'admin')
    clash = post(admin.client, f'/admin/users/{user_id}/edit', {'username': 'TAKEN', 'email': ''})
    assert clash.status_code == 200 and b'already in use' in clash.data
    post(admin.client, f'/admin/users/{user_id}/edit',
         {'username': 'mine', 'email': '', 'role': 'faculty', 'faculty_id': '1', 'is_active': '0'})
    row = users(app, 'user_id = %s', (user_id,))[0]
    assert row['role'] == 'admin' and row['faculty_id'] is None and row['is_active'] == 1


def test_deactivating_blocks_login_and_activating_restores_it(app, admin):
    with app.app_context():
        user_id = make_user('victim', 'admin')
    assert post(admin.client, f'/admin/users/{user_id}/deactivate').status_code == 302
    assert login(app.test_client(), 'victim').status_code == 200          # refused
    assert post(admin.client, f'/admin/users/{user_id}/activate').status_code == 302
    assert login(app.test_client(), 'victim').status_code == 302


def test_an_admin_cannot_deactivate_their_own_account(app, admin):
    response = post(admin.client, f'/admin/users/{admin.user_id}/deactivate', follow_redirects=True)
    assert b'your own account' in response.data
    assert users(app, 'user_id = %s', (admin.user_id,))[0]['is_active'] == 1


def test_the_last_active_administrator_cannot_be_deactivated(ctx):
    only = make_user('only', 'admin')
    with pytest.raises(ValidationError, match='administrator'):
        auth_service.set_active(only, False)
    other = make_user('other', 'admin')
    auth_service.set_active(only, False)             # fine now: 'other' remains
    with pytest.raises(ValidationError, match='administrator'):
        auth_service.set_active(other, False)


def test_resetting_a_password_replaces_it_signs_the_user_out_and_forces_a_change(app, admin):
    with app.app_context():
        user_id = make_user('forgetful', 'admin')
    victim = app.test_client()
    login(victim, 'forgetful')
    assert victim.get('/admin').status_code == 200

    response = post(admin.client, f'/admin/users/{user_id}/reset-password')
    assert response.status_code == 200
    temporary = shown_password(response)

    assert victim.get('/admin').status_code == 302                         # old session is dead
    assert login(app.test_client(), 'forgetful', PASSWORD).status_code == 200   # old password is dead
    fresh = login(app.test_client(), 'forgetful', temporary)
    assert fresh.headers['Location'].endswith('/account/password')
    assert users(app, 'user_id = %s', (user_id,))[0]['must_change_password'] == 1
    assert 'user.reset_password' in audit_text(app) and temporary not in audit_text(app)


def test_password_reset_needs_post_and_csrf(app, admin):
    with app.app_context():
        user_id = make_user('target', 'admin')
    assert admin.client.get(f'/admin/users/{user_id}/reset-password').status_code == 405
    assert post(admin.client, f'/admin/users/{user_id}/reset-password', {'csrf_token': None}).status_code == 400
    with app.app_context():
        assert auth_service.authenticate('target', PASSWORD) is not None


def test_acting_on_an_unknown_account_is_not_found(admin):
    assert admin.client.get('/admin/users/99999/edit').status_code == 404
    assert post(admin.client, '/admin/users/99999/reset-password').status_code == 404
    assert post(admin.client, '/admin/users/99999/deactivate').status_code == 404


# ---- listing ----------------------------------------------------------------

def test_user_list_filters_by_role_and_search_and_hides_hashes(app, admin):
    with app.app_context():
        make_user('alpha', 'admin', email='alpha@example.test')
        make_user('bravo', 'faculty', faculty_id=make_faculty('F1', 'Prof Bravo'))
    everything = admin.client.get('/admin/users').data
    assert b'alpha' in everything and b'bravo' in everything
    assert b'scrypt' not in everything and b'password_hash' not in everything
    faculty_only = admin.client.get('/admin/users?role=faculty').data
    assert b'bravo' in faculty_only and b'alpha' not in faculty_only
    assert b'alpha@example.test' in admin.client.get('/admin/users?search=alpha@').data
    assert admin.client.get('/admin/users?role=nonsense&page=zzz').status_code == 200


def test_the_user_list_pages(app, admin):
    with app.app_context():
        for index in range(30):
            make_user(f'person{index:02}', 'admin')
    assert b'person00' in admin.client.get('/admin/users?search=person').data
    assert b'person29' in admin.client.get('/admin/users?search=person&page=2').data
