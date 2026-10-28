import pytest

from db import execute_query
from services import auth_service
from services.validation import ValidationError
from tests.factories import PASSWORD, make_faculty, make_student, make_user


def stored(username):
    return execute_query('SELECT * FROM users WHERE username = %s', (username,))[0]


# ---- hashing and policy -----------------------------------------------------

def test_hash_is_salted_and_never_the_plaintext():
    first = auth_service.hash_password(PASSWORD)
    second = auth_service.hash_password(PASSWORD)
    assert PASSWORD not in first
    assert first != second
    assert auth_service.check_password(first, PASSWORD)
    assert not auth_service.check_password(first, PASSWORD + 'x')


@pytest.mark.parametrize('password, username, fragment', [
    ('short', 'asha', 'at least 10'),
    ('x' * 129, 'asha', 'at most 128'),
    ('Asha-Rao-01', 'asha-rao-01', 'username'),
])
def test_password_policy_rejects(password, username, fragment):
    with pytest.raises(ValidationError, match=fragment):
        auth_service.validate_new_password(password, username)


def test_password_policy_accepts_a_reasonable_password():
    auth_service.validate_new_password(PASSWORD, 'asha')


def test_temporary_passwords_meet_the_policy_and_differ():
    first = auth_service.generate_temporary_password()
    second = auth_service.generate_temporary_password()
    auth_service.validate_new_password(first, 'anyone')
    assert first != second


# ---- creating accounts ------------------------------------------------------

def test_create_user_stores_a_hash_not_the_password(ctx):
    make_user('admin1', 'admin')
    row = stored('admin1')
    assert row['password_hash'] != PASSWORD
    assert PASSWORD not in row['password_hash']
    assert row['role'] == 'admin' and row['is_active'] == 1


def test_create_user_without_a_password_is_refused(ctx):
    with pytest.raises(ValidationError, match='password'):
        auth_service.create_user('nopass', 'admin', password=None)


def test_create_user_rejects_weak_passwords(ctx):
    with pytest.raises(ValidationError, match='at least 10'):
        auth_service.create_user('weak', 'admin', password='short')


def test_usernames_and_emails_are_unique_ignoring_case(ctx):
    make_user('Asha', 'admin', email='asha@example.test')
    with pytest.raises(ValidationError, match='username'):
        make_user('asha', 'admin')
    with pytest.raises(ValidationError, match='email'):
        make_user('other', 'admin', email='ASHA@example.test')


def test_unknown_roles_are_refused(ctx):
    with pytest.raises(ValidationError, match='role'):
        make_user('root', 'superuser')


def test_student_accounts_need_an_existing_unlinked_student_record(ctx):
    with pytest.raises(ValidationError, match='student'):
        make_user('stu0', 'student')
    with pytest.raises(ValidationError, match='student'):
        make_user('stu0', 'student', student_id=9999)
    student_id = make_student()
    make_user('stu1', 'student', student_id=student_id)
    with pytest.raises(ValidationError, match='already has an account'):
        make_user('stu2', 'student', student_id=student_id)


def test_faculty_accounts_need_an_existing_faculty_record(ctx):
    with pytest.raises(ValidationError, match='faculty'):
        make_user('fac0', 'faculty')
    make_user('fac1', 'faculty', faculty_id=make_faculty())


def test_admin_accounts_cannot_carry_a_student_link(ctx):
    with pytest.raises(ValidationError, match='admin'):
        make_user('adm1', 'admin', student_id=make_student())


def test_get_user_never_exposes_the_hash(ctx):
    user_id = make_user('admin1', 'admin')
    user = auth_service.get_user(user_id)
    assert user['username'] == 'admin1'
    assert 'password_hash' not in user
    assert auth_service.get_user(99999) is None


# ---- authenticating ---------------------------------------------------------

def test_authenticate_by_username_or_email_ignoring_case(ctx):
    make_user('Asha', 'admin', email='asha@example.test')
    assert auth_service.authenticate('asha', PASSWORD)['username'] == 'Asha'
    assert auth_service.authenticate('ASHA@example.test', PASSWORD)['username'] == 'Asha'


def test_authenticate_records_the_login_time(ctx):
    make_user('asha', 'admin')
    assert stored('asha')['last_login_at'] is None
    auth_service.authenticate('asha', PASSWORD)
    assert stored('asha')['last_login_at'] is not None


def test_wrong_password_unknown_user_and_blank_input_all_fail_the_same_way(ctx):
    make_user('asha', 'admin')
    assert auth_service.authenticate('asha', 'wrong-password-1') is None
    assert auth_service.authenticate('nobody', PASSWORD) is None
    assert auth_service.authenticate('', PASSWORD) is None
    assert auth_service.authenticate('asha', '') is None


def test_unknown_users_still_cost_a_hash_check(ctx, monkeypatch):
    calls = []
    real = auth_service.check_password
    monkeypatch.setattr(auth_service, 'check_password',
                        lambda h, p: calls.append(1) or real(h, p))
    auth_service.authenticate('nobody-here', PASSWORD)
    assert calls == [1]


def test_deactivated_accounts_cannot_log_in(ctx):
    make_user('backup', 'admin')
    user_id = make_user('asha', 'admin')
    auth_service.set_active(user_id, False)
    assert auth_service.authenticate('asha', PASSWORD) is None


# ---- changing credentials and status ----------------------------------------

def test_set_password_replaces_the_credential_and_ends_old_sessions(ctx):
    user_id = make_user('asha', 'admin')
    before = auth_service.get_user(user_id)['session_version']
    auth_service.set_password(user_id, 'Brand-New-Pass-7', must_change_password=True)
    after = auth_service.get_user(user_id)
    assert auth_service.authenticate('asha', PASSWORD) is None
    assert auth_service.authenticate('asha', 'Brand-New-Pass-7') is not None
    assert after['session_version'] == before + 1
    assert after['must_change_password'] == 1


def test_set_password_applies_the_policy(ctx):
    user_id = make_user('asha', 'admin')
    with pytest.raises(ValidationError):
        auth_service.set_password(user_id, 'short')
    assert auth_service.authenticate('asha', PASSWORD) is not None


def test_changing_active_status_ends_old_sessions(ctx):
    make_user('backup', 'admin')
    user_id = make_user('asha', 'admin')
    before = auth_service.get_user(user_id)['session_version']
    auth_service.set_active(user_id, False)
    assert auth_service.get_user(user_id)['session_version'] == before + 1
