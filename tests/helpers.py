from tests.conftest import DATABASE_DIR, run_script

SETUP_ORDER = [
    'schema.sql',
    'seed.sql',
    'migration_add_assessments.sql',
    'seed_vit_students.sql',
]
BASE_SCHEMA = ['schema.sql', 'migration_add_assessments.sql']
COUNTED_TABLES = ['students', 'subjects', 'examinations', 'marks', 'assessments', 'assessment_marks']


def apply_scripts(connection, db_name, names):
    for name in names:
        run_script(connection, DATABASE_DIR / name, db_name)


def apply_setup(connection, db_name):
    """The documented new-install order, sample data included."""
    apply_scripts(connection, db_name, SETUP_ORDER)


def table_counts(connection, tables=COUNTED_TABLES):
    cursor = connection.cursor()
    counts = {}
    for table in tables:
        cursor.execute(f'SELECT COUNT(*) FROM {table}')
        counts[table] = cursor.fetchone()[0]
    cursor.close()
    return counts


# ---- browser-like helpers for route tests -----------------------------------

def csrf(client):
    """The client's CSRF token, as if it had already loaded a page."""
    import secrets
    with client.session_transaction() as session:
        return session.setdefault('_csrf', secrets.token_urlsafe(32))


def post(client, path, data=None, **kwargs):
    """POST with a valid CSRF token unless the caller supplies one (or None)."""
    data = dict(data or {})
    if 'csrf_token' not in data:
        data['csrf_token'] = csrf(client)
    elif data['csrf_token'] is None:
        del data['csrf_token']
    return client.post(path, data=data, **kwargs)


def login(client, username, password=None, **kwargs):
    from tests.factories import PASSWORD
    return post(client, '/login',
                {'username': username, 'password': PASSWORD if password is None else password},
                **kwargs)
