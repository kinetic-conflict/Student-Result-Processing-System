import os
from datetime import timedelta

MIN_SECRET_KEY_LENGTH = 32
PLACEHOLDER_SECRET_KEYS = {
    'dev-secret-key-change-in-production',
    'changeme',
    'change-me',
    'secret',
    'your_secret_key',
}
TRUE_VALUES = {'1', 'true', 'yes', 'on'}


class ConfigError(RuntimeError):
    """Raised at startup when the environment is missing or has bad settings."""


def _flag(value):
    return str(value).strip().lower() in TRUE_VALUES


def _positive_int(env, name, default, problems):
    raw = env.get(name)
    if raw is None or str(raw).strip() == '':
        return default
    try:
        value = int(str(raw).strip())
    except ValueError:
        problems.append(f'{name} must be a whole number.')
        return default
    if value < 1:
        problems.append(f'{name} must be at least 1.')
        return default
    return value


def build_config(env=None):
    """Turn environment-style settings into a validated Flask config dict.

    Collects every problem and raises one ConfigError, so a fresh checkout
    shows everything that needs fixing in a single run. Error text never
    includes setting values.
    """
    env = os.environ if env is None else env
    problems = []

    secret_key = env.get('SECRET_KEY', '')
    if not secret_key:
        problems.append(
            'SECRET_KEY is not set. Generate one with '
            '`python -c "import secrets; print(secrets.token_hex(32))"` '
            'and put it in your .env file.'
        )
    elif secret_key in PLACEHOLDER_SECRET_KEYS or len(secret_key) < MIN_SECRET_KEY_LENGTH:
        problems.append(
            f'SECRET_KEY is a placeholder or shorter than {MIN_SECRET_KEY_LENGTH} '
            'characters. Generate a new one with '
            '`python -c "import secrets; print(secrets.token_hex(32))"`.'
        )

    if not env.get('DB_PASSWORD'):
        problems.append('DB_PASSWORD is not set. Add your MySQL password to your .env file.')

    db_port = _positive_int(env, 'DB_PORT', 3306, problems)
    app_port = _positive_int(env, 'APP_PORT', 5000, problems)
    idle_minutes = _positive_int(env, 'SESSION_IDLE_MINUTES', 30, problems)
    max_failures = _positive_int(env, 'LOGIN_MAX_FAILURES', 5, problems)
    max_failures_per_ip = _positive_int(env, 'LOGIN_MAX_FAILURES_PER_IP', 20, problems)
    window_minutes = _positive_int(env, 'LOGIN_WINDOW_MINUTES', 15, problems)

    if problems:
        raise ConfigError('Configuration problems:\n- ' + '\n- '.join(problems))

    return {
        'SECRET_KEY': secret_key,
        'DB_HOST': env.get('DB_HOST') or 'localhost',
        'DB_PORT': db_port,
        'DB_USER': env.get('DB_USER') or 'root',
        'DB_PASSWORD': env['DB_PASSWORD'],
        'DB_NAME': env.get('DB_NAME') or 'student_result_db',
        'DEBUG': _flag(env.get('FLASK_DEBUG', '0')),
        'APP_HOST': env.get('APP_HOST') or '127.0.0.1',
        'APP_PORT': app_port,
        'SESSION_COOKIE_HTTPONLY': True,
        'SESSION_COOKIE_SAMESITE': 'Lax',
        'SESSION_COOKIE_SECURE': _flag(env.get('SESSION_COOKIE_SECURE', '0')),
        'PERMANENT_SESSION_LIFETIME': timedelta(minutes=idle_minutes),
        'MAX_CONTENT_LENGTH': 1_000_000,   # forms only; there are no uploads
        'LOGIN_MAX_FAILURES': max_failures,
        'LOGIN_MAX_FAILURES_PER_IP': max_failures_per_ip,
        'LOGIN_WINDOW_SECONDS': window_minutes * 60,
    }
