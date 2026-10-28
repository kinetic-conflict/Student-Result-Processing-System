import time
from urllib.parse import parse_qs, urlsplit

import pytest

from app import create_app
from services import auth_service
from tests.conftest import app_settings
from tests.factories import PASSWORD, make_user
from tests.helpers import csrf, login, post


@pytest.fixture
def admin(ctx):
    make_user('asha', 'admin', email='asha@example.test')
    return 'asha'


def location(response):
    return response.headers['Location']


# ---- the login page ---------------------------------------------------------

def test_login_page_has_a_csrf_field_and_is_not_cached(client):
    response = client.get('/login')
    assert response.status_code == 200
    assert b'name="csrf_token"' in response.data
    assert 'no-store' in response.headers['Cache-Control']


def test_login_without_a_csrf_token_is_rejected(client, admin):
    response = post(client, '/login', {'username': admin, 'password': PASSWORD, 'csrf_token': None})
    assert response.status_code == 400


def test_login_with_a_wrong_csrf_token_is_rejected(client, admin):
    csrf(client)
    response = post(client, '/login', {'username': admin, 'password': PASSWORD, 'csrf_token': 'forged'})
    assert response.status_code == 400


# ---- logging in -------------------------------------------------------------

def test_valid_login_lands_on_the_admin_dashboard(client, admin):
    response = login(client, admin)
    assert response.status_code == 302
    assert location(response).endswith('/admin')
    assert client.get('/admin').status_code == 200


def test_login_accepts_the_email_address(client, admin):
    assert login(client, 'ASHA@example.test').status_code == 302


def test_login_discards_any_session_that_existed_before(client, admin):
    with client.session_transaction() as session:
        session['planted'] = 'attacker-value'
    login(client, admin)
    with client.session_transaction() as session:
        assert 'planted' not in session
        assert session['uid']


def test_wrong_password_and_unknown_user_look_identical(client, admin):
    wrong_password = login(client, admin, 'not-the-password-1')
    unknown_user = login(client, 'nobody-by-this-name', PASSWORD)
    for response in (wrong_password, unknown_user):
        assert response.status_code == 200
        assert b'Invalid username or password.' in response.data
    assert wrong_password.data.count(b'alert') == unknown_user.data.count(b'alert')


def test_missing_fields_are_reported(client, admin):
    response = post(client, '/login', {'username': '', 'password': ''})
    assert response.status_code == 200
    assert b'Enter your username or email and your password.' in response.data


def test_the_password_is_never_echoed_back(client, admin):
    response = login(client, admin, 'a-secret-that-is-wrong')
    assert b'a-secret-that-is-wrong' not in response.data


def test_next_must_stay_on_this_site(client, admin):
    for hostile in ('https://evil.example/', '//evil.example/', '/\\evil.example', 'javascript:alert(1)'):
        with client.session_transaction() as session:
            session.clear()
        response = post(client, f'/login?next={hostile}', {'username': admin, 'password': PASSWORD})
        assert location(response).endswith('/admin'), hostile


def test_next_is_honoured_for_local_paths(client, admin):
    response = post(client, '/login?next=/students', {'username': admin, 'password': PASSWORD})
    assert location(response).endswith('/students')


# ---- lockout ----------------------------------------------------------------

def test_repeated_failures_lock_the_account_even_for_the_right_password(client, admin):
    for _ in range(5):
        login(client, admin, 'wrong-password-1')
    response = login(client, admin)
    assert response.status_code == 429
    assert b'Too many failed attempts' in response.data
    with client.session_transaction() as session:
        assert 'uid' not in session


def test_a_lockout_does_not_leak_whether_the_account_exists(client, admin):
    for _ in range(5):
        login(client, 'no-such-account', 'wrong-password-1')
    assert login(client, 'no-such-account').status_code == 429


def test_one_locked_account_does_not_block_another(client, admin, ctx):
    make_user('ravi', 'admin')
    for _ in range(5):
        login(client, admin, 'wrong-password-1')
    assert login(client, 'ravi').status_code == 302


def test_one_address_cannot_spray_many_usernames(server, clean_db):
    settings = dict(app_settings(server, clean_db), LOGIN_MAX_FAILURES_PER_IP='3')
    spray = create_app(settings, testing=True).test_client()
    for index in range(3):
        login(spray, f'guess-{index}', 'wrong-password-1')
    assert login(spray, 'a-fresh-name', 'wrong-password-1').status_code == 429


def test_success_clears_earlier_failures(client, admin):
    for _ in range(4):
        login(client, admin, 'wrong-password-1')
    assert login(client, admin).status_code == 302
    client.post('/logout', data={'csrf_token': csrf(client)})
    for _ in range(4):
        login(client, admin, 'wrong-password-1')
    assert login(client, admin).status_code == 302


# ---- logging out ------------------------------------------------------------

def test_logout_needs_post_and_a_csrf_token(client, admin):
    login(client, admin)
    assert client.get('/logout').status_code == 405
    assert post(client, '/logout', {'csrf_token': 'forged'}).status_code == 400
    assert client.get('/admin').status_code == 200


def test_logout_ends_the_session(client, admin):
    login(client, admin)
    response = post(client, '/logout')
    assert response.status_code == 302 and location(response).endswith('/login')
    assert client.get('/admin').status_code == 302


def test_a_copied_cookie_stops_working_after_logout(client, admin, app):
    login(client, admin)
    stolen = client.get_cookie('session').value
    post(client, '/logout')
    thief = app.test_client()
    thief.set_cookie('session', stolen)
    assert thief.get('/admin').status_code == 302


# ---- protected pages --------------------------------------------------------

def test_anonymous_visitors_are_sent_to_login_and_back(client):
    response = client.get('/students')
    assert response.status_code == 302
    target = urlsplit(location(response))
    assert target.path == '/login'
    assert parse_qs(target.query)['next'] == ['/students']


def test_signed_in_users_skip_the_login_page(client, admin):
    login(client, admin)
    assert location(client.get('/login')).endswith('/admin')


def test_deactivating_an_account_ends_its_open_session(client, admin, ctx):
    make_user('backup', 'admin')           # the last active administrator cannot be deactivated
    login(client, admin)
    assert client.get('/admin').status_code == 200
    user = auth_service.authenticate(admin, PASSWORD)
    auth_service.set_active(user['user_id'], False)
    assert client.get('/admin').status_code == 302


def test_resetting_the_password_ends_open_sessions(client, admin, ctx):
    login(client, admin)
    user = auth_service.authenticate(admin, PASSWORD)
    auth_service.set_password(user['user_id'], 'Reset-By-Admin-42', must_change_password=True)
    assert client.get('/admin').status_code == 302


def test_sessions_have_an_absolute_lifetime(client, admin):
    login(client, admin)
    with client.session_transaction() as session:
        session['iat'] = int(time.time()) - 13 * 3600
    assert client.get('/admin').status_code == 302


def test_session_cookie_is_httponly_samesite_and_expires(client, admin):
    response = login(client, admin)
    cookie = next(c for c in response.headers.getlist('Set-Cookie') if c.startswith('session='))
    assert 'HttpOnly' in cookie
    assert 'SameSite=Lax' in cookie
    assert 'Expires=' in cookie or 'Max-Age=' in cookie


# ---- forced password change -------------------------------------------------

@pytest.fixture
def temp_user(ctx):
    auth_service.create_user('newbie', 'admin', password='Temporary-Pass-1', must_change_password=True)
    return 'newbie'


def test_a_temporary_password_forces_a_change_before_anything_else(client, temp_user):
    response = login(client, temp_user, 'Temporary-Pass-1')
    assert location(response).endswith('/account/password')
    assert location(client.get('/admin')).endswith('/account/password')
    assert location(client.get('/students')).endswith('/account/password')
    assert client.get('/account/password').status_code == 200


def test_changing_the_password_clears_the_flag_and_keeps_the_user_signed_in(client, temp_user):
    login(client, temp_user, 'Temporary-Pass-1')
    response = post(client, '/account/password', {
        'current_password': 'Temporary-Pass-1',
        'new_password': 'My-Own-Password-9',
        'confirm_password': 'My-Own-Password-9'})
    assert response.status_code == 302
    assert client.get('/admin').status_code == 200
    other = client.application.test_client()
    assert login(other, temp_user, 'Temporary-Pass-1').status_code == 200   # old one is dead
    assert login(other, temp_user, 'My-Own-Password-9').status_code == 302


@pytest.mark.parametrize('current, new, confirm, message', [
    ('wrong-current-1', 'My-Own-Password-9', 'My-Own-Password-9', b'current password is incorrect'),
    ('Temporary-Pass-1', 'My-Own-Password-9', 'Different-Pass-9', b'do not match'),
    ('Temporary-Pass-1', 'short', 'short', b'at least 10'),
    ('Temporary-Pass-1', 'Temporary-Pass-1', 'Temporary-Pass-1', b'must be different'),
])
def test_password_change_validation(client, temp_user, current, new, confirm, message):
    login(client, temp_user, 'Temporary-Pass-1')
    response = post(client, '/account/password', {
        'current_password': current, 'new_password': new, 'confirm_password': confirm})
    assert response.status_code == 200
    assert message in response.data


# ---- CSRF and headers on the rest of the app --------------------------------

def test_every_state_changing_form_needs_the_token(client, admin):
    login(client, admin)
    response = post(client, '/students/add', {'registration_number': 'X1', 'csrf_token': None})
    assert response.status_code == 400


def test_security_headers_are_present(client, admin):
    login(client, admin)
    response = client.get('/admin')
    assert response.headers['X-Content-Type-Options'] == 'nosniff'
    assert response.headers['X-Frame-Options'] == 'DENY'
    assert response.headers['Referrer-Policy'] == 'same-origin'
    assert "default-src 'self'" in response.headers['Content-Security-Policy']
    assert 'no-store' in response.headers['Cache-Control']


def test_unknown_urls_get_a_plain_error_page(client, admin):
    login(client, admin)
    response = client.get('/no/such/page')
    assert response.status_code == 404
    assert b'Traceback' not in response.data and b'File "' not in response.data
