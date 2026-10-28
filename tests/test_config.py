import pytest

from config import ConfigError, build_config

GOOD = {
    'SECRET_KEY': 'a' * 48,
    'DB_USER': 'app_user',
    'DB_PASSWORD': 'not-a-real-password',
    'DB_NAME': 'student_result_db',
}


def env(**overrides):
    merged = dict(GOOD)
    merged.update(overrides)
    return {k: v for k, v in merged.items() if v is not None}


def test_missing_secret_key_names_the_variable_and_how_to_make_one():
    with pytest.raises(ConfigError) as exc:
        build_config(env(SECRET_KEY=None))
    message = str(exc.value)
    assert 'SECRET_KEY' in message
    assert 'secrets.token_hex' in message


@pytest.mark.parametrize('weak', [
    'dev-secret-key-change-in-production',
    'changeme',
    'short',
    'x' * 31,
])
def test_weak_or_placeholder_secret_key_is_rejected(weak):
    with pytest.raises(ConfigError, match='SECRET_KEY'):
        build_config(env(SECRET_KEY=weak))


def test_missing_db_password_is_rejected_without_echoing_other_values():
    with pytest.raises(ConfigError) as exc:
        build_config(env(DB_PASSWORD=None))
    assert 'DB_PASSWORD' in str(exc.value)
    assert GOOD['SECRET_KEY'] not in str(exc.value)


def test_non_numeric_port_names_the_variable():
    with pytest.raises(ConfigError, match='DB_PORT'):
        build_config(env(DB_PORT='abc'))


def test_safe_defaults():
    cfg = build_config(env())
    assert cfg['DEBUG'] is False
    assert cfg['APP_HOST'] == '127.0.0.1'
    assert cfg['DB_HOST'] == 'localhost'
    assert cfg['DB_PORT'] == 3306
    assert cfg['SESSION_COOKIE_HTTPONLY'] is True
    assert cfg['SESSION_COOKIE_SAMESITE'] == 'Lax'
    assert cfg['SESSION_COOKIE_SECURE'] is False


def test_debug_needs_an_explicit_opt_in():
    assert build_config(env(FLASK_DEBUG='1'))['DEBUG'] is True
    assert build_config(env(FLASK_DEBUG='0'))['DEBUG'] is False
    assert build_config(env(FLASK_DEBUG='false'))['DEBUG'] is False


def test_secure_cookie_flag_can_be_enabled():
    assert build_config(env(SESSION_COOKIE_SECURE='1'))['SESSION_COOKIE_SECURE'] is True


def test_session_lifetime_is_bounded():
    cfg = build_config(env())
    assert cfg['PERMANENT_SESSION_LIFETIME'].total_seconds() == 30 * 60
    with pytest.raises(ConfigError, match='SESSION_IDLE_MINUTES'):
        build_config(env(SESSION_IDLE_MINUTES='0'))


def test_login_throttle_limits_have_defaults_and_can_be_tuned():
    cfg = build_config(env())
    assert cfg['LOGIN_MAX_FAILURES'] == 5
    assert cfg['LOGIN_MAX_FAILURES_PER_IP'] == 20
    assert cfg['LOGIN_WINDOW_SECONDS'] == 15 * 60
    assert build_config(env(LOGIN_MAX_FAILURES='2'))['LOGIN_MAX_FAILURES'] == 2


def test_request_bodies_are_size_limited():
    assert 0 < build_config(env())['MAX_CONTENT_LENGTH'] <= 2_000_000
