"""Accounts and credentials: hashing, password policy, lookup, login checks.

Framework-free on purpose. Sessions, cookies and redirects live in security.py.
"""
import re
import secrets

from werkzeug.security import check_password_hash, generate_password_hash

from db import execute_query, execute_update, is_duplicate_error, like_contains, transaction
from services.validation import EMAIL, ValidationError

ROLE_ADMIN = 'admin'
ROLE_FACULTY = 'faculty'
ROLE_STUDENT = 'student'
ROLES = (ROLE_ADMIN, ROLE_FACULTY, ROLE_STUDENT)

MIN_PASSWORD_LENGTH = 10
MAX_PASSWORD_LENGTH = 128
USERNAME = re.compile(r'[A-Za-z0-9._-]{3,50}')

# Public columns only. password_hash is read inside this module and nowhere else.
USER_COLUMNS = ('user_id, username, email, role, is_active, must_change_password, '
                'session_version, student_id, faculty_id, last_login_at')

# Checked when a login names no real account, so unknown and known users cost the same.
_DUMMY_HASH = generate_password_hash('placeholder-for-unknown-accounts')


def hash_password(password):
    return generate_password_hash(password)


def check_password(password_hash, password):
    try:
        return check_password_hash(password_hash, password)
    except ValueError:  # malformed stored hash
        return False


def validate_new_password(password, username=None):
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValidationError(f'Password must be at least {MIN_PASSWORD_LENGTH} characters.')
    if len(password) > MAX_PASSWORD_LENGTH:
        raise ValidationError(f'Password must be at most {MAX_PASSWORD_LENGTH} characters.')
    if username and password.lower() == username.lower():
        raise ValidationError('Password must not be the same as the username.')


def generate_temporary_password():
    return secrets.token_urlsafe(12)


def _validate_identity(username, email, exclude_user_id=0):
    if not USERNAME.fullmatch(username or ''):
        raise ValidationError('Username must be 3-50 letters, digits, dots, dashes or underscores.')
    if email is not None and (len(email) > 100 or not EMAIL.fullmatch(email)):
        raise ValidationError('Enter a valid email address.')
    if execute_query('SELECT 1 FROM users WHERE username = %s AND user_id <> %s',
                     (username, exclude_user_id)):
        raise ValidationError('That username is already in use.')
    if email and execute_query('SELECT 1 FROM users WHERE email = %s AND user_id <> %s',
                               (email, exclude_user_id)):
        raise ValidationError('That email is already in use.')


def _validate_links(role, student_id, faculty_id):
    if role not in ROLES:
        raise ValidationError('Choose a valid role (admin, faculty or student).')
    if role == ROLE_ADMIN and (student_id or faculty_id):
        raise ValidationError('admin accounts cannot be linked to a student or faculty record.')
    if role == ROLE_STUDENT:
        if faculty_id:
            raise ValidationError('Student accounts cannot be linked to a faculty record.')
        _require_free_record('student', 'students', 'student_id', student_id)
    if role == ROLE_FACULTY:
        if student_id:
            raise ValidationError('Faculty accounts cannot be linked to a student record.')
        _require_free_record('faculty', 'faculty', 'faculty_id', faculty_id)


def _require_free_record(noun, table, key, record_id):
    if not record_id:
        raise ValidationError(f'{noun.capitalize()} accounts must be linked to a {noun} record.')
    if not execute_query(f'SELECT 1 FROM {table} WHERE {key} = %s', (record_id,)):
        raise ValidationError(f'That {noun} record does not exist.')
    if execute_query(f'SELECT 1 FROM users WHERE {key} = %s', (record_id,)):
        raise ValidationError(f'That {noun} record already has an account.')


def create_user(username, role, *, email=None, student_id=None, faculty_id=None,
                password=None, must_change_password=True):
    """Create an account and return its id. Raises ValidationError with a user-safe message."""
    username = (username or '').strip()
    email = (email or '').strip() or None
    if not password:
        raise ValidationError('A password is required.')
    _validate_identity(username, email)
    _validate_links(role, student_id, faculty_id)
    validate_new_password(password, username)
    try:
        return execute_update(
            'INSERT INTO users (username, email, password_hash, role, student_id, faculty_id, '
            'must_change_password) VALUES (%s, %s, %s, %s, %s, %s, %s)',
            (username, email, hash_password(password), role, student_id, faculty_id,
             1 if must_change_password else 0))
    except Exception as error:
        if is_duplicate_error(error):  # lost a race with another request
            raise ValidationError('That username, email or record is already in use.') from error
        raise


def get_user(user_id):
    rows = execute_query(f'SELECT {USER_COLUMNS} FROM users WHERE user_id = %s', (user_id,))
    return rows[0] if rows else None


def authenticate(identifier, password):
    """Return the user for a valid username-or-email and password, else None."""
    identifier = (identifier or '').strip()
    if not identifier or not password:
        return None
    rows = execute_query(
        'SELECT user_id, password_hash, is_active FROM users WHERE username = %s OR email = %s LIMIT 1',
        (identifier, identifier))
    row = rows[0] if rows else None
    password_ok = check_password(row['password_hash'] if row else _DUMMY_HASH, password)
    if not row or not password_ok or not row['is_active']:
        return None
    execute_update('UPDATE users SET last_login_at = NOW() WHERE user_id = %s', (row['user_id'],))
    return get_user(row['user_id'])


def verify_password(user_id, password):
    """True when `password` is the stored credential for this account."""
    rows = execute_query('SELECT password_hash FROM users WHERE user_id = %s', (user_id,))
    return bool(rows) and check_password(rows[0]['password_hash'], password)


def revoke_sessions(user_id):
    """Sign the user out everywhere: every cookie issued before now stops working."""
    execute_update('UPDATE users SET session_version = session_version + 1 WHERE user_id = %s',
                   (user_id,))


def set_password(user_id, new_password, must_change_password=False):
    """Replace the credential and sign the user out everywhere."""
    user = get_user(user_id)
    if user is None:
        raise ValidationError('That account does not exist.')
    validate_new_password(new_password, user['username'])
    execute_update(
        'UPDATE users SET password_hash = %s, must_change_password = %s, '
        'session_version = session_version + 1 WHERE user_id = %s',
        (hash_password(new_password), 1 if must_change_password else 0, user_id))


def set_active(user_id, active):
    """Enable or disable an account (disabling also signs the user out everywhere).

    The last active administrator cannot be disabled, so the system is never locked out.
    """
    with transaction() as cursor:
        # Lock every active admin row first, always in id order. Two admins deactivating each
        # other at once then take turns (no deadlock) and the second one sees the first's result.
        cursor.execute("SELECT user_id FROM users WHERE role = 'admin' AND is_active = 1 "
                       'ORDER BY user_id FOR UPDATE')
        active_admins = {row['user_id'] for row in cursor.fetchall()}
        if not active and user_id in active_admins and not active_admins - {user_id}:
            raise ValidationError('At least one active administrator must remain.')
        cursor.execute(
            'UPDATE users SET is_active = %s, session_version = session_version + 1 WHERE user_id = %s',
            (1 if active else 0, user_id))


def update_account(user_id, username, email):
    """Change a login name and email. Role and linked record are fixed at creation."""
    if get_user(user_id) is None:
        raise LookupError('That account does not exist.')
    username = (username or '').strip()
    email = (email or '').strip() or None
    _validate_identity(username, email, exclude_user_id=user_id)
    execute_update('UPDATE users SET username = %s, email = %s WHERE user_id = %s',
                   (username, email, user_id))


LIST_USERS = (
    'SELECT u.user_id, u.username, u.email, u.role, u.is_active, u.must_change_password, '
    'u.last_login_at, COALESCE(s.full_name, f.full_name) AS display_name, '
    'COALESCE(s.registration_number, f.employee_id) AS record_code '
    'FROM users u LEFT JOIN students s ON s.student_id = u.student_id '
    'LEFT JOIN faculty f ON f.faculty_id = u.faculty_id'
)


def _user_filter(search, role):
    where, params = ' WHERE 1 = 1', []
    if role in ROLES:
        where += ' AND u.role = %s'
        params.append(role)
    if search:
        pattern = like_contains(search)
        where += (' AND (u.username LIKE %s OR u.email LIKE %s OR s.full_name LIKE %s '
                  'OR f.full_name LIKE %s)')
        params += [pattern] * 4
    return where, params


def count_users(search=None, role=None):
    where, params = _user_filter(search, role)
    return execute_query('SELECT COUNT(*) AS n FROM users u '
                         'LEFT JOIN students s ON s.student_id = u.student_id '
                         f'LEFT JOIN faculty f ON f.faculty_id = u.faculty_id{where}',
                         tuple(params))[0]['n']


def list_users(search=None, role=None, limit=25, offset=0):
    where, params = _user_filter(search, role)
    return execute_query(f'{LIST_USERS}{where} ORDER BY u.username LIMIT %s OFFSET %s',
                         (*params, limit, offset))


def unlinked_students():
    return execute_query(
        'SELECT s.student_id, s.registration_number, s.full_name FROM students s '
        'LEFT JOIN users u ON u.student_id = s.student_id WHERE u.user_id IS NULL '
        'ORDER BY s.registration_number')


def unlinked_faculty():
    return execute_query(
        'SELECT f.faculty_id, f.employee_id, f.full_name FROM faculty f '
        'LEFT JOIN users u ON u.faculty_id = f.faculty_id WHERE u.user_id IS NULL AND f.is_active = 1 '
        'ORDER BY f.employee_id')


BULK_LIMIT = 200


def create_accounts_for(role):
    """Give every student (or active faculty member) without an account one.

    The login name is the registration number (or employee id), lower-cased, and each
    account gets its own random temporary password that must be changed at first sign-in.
    Returns (created, skipped): created is [(username, display name, temporary password)],
    skipped is [(code, reason)] for records that could not be given an account.
    """
    if role == ROLE_STUDENT:
        records = [(r['registration_number'], r['full_name'], {'student_id': r['student_id']})
                   for r in unlinked_students()]
    elif role == ROLE_FACULTY:
        records = [(r['employee_id'], r['full_name'], {'faculty_id': r['faculty_id']})
                   for r in unlinked_faculty()]
    else:
        raise ValidationError('Bulk creation is only available for students and faculty.')

    created, skipped = [], []
    for code, name, links in records[:BULK_LIMIT]:
        username, temporary = code.lower(), generate_temporary_password()
        try:
            create_user(username, role, password=temporary, must_change_password=True, **links)
        except ValidationError as error:
            skipped.append((code, str(error)))
        else:
            created.append((username, name, temporary))
    return created, skipped
