"""Shared fixtures.

Database tests need a throwaway MySQL server. Point these variables at one
(never at a server holding real data) and every test creates and drops its own
uniquely named `srps_test_*` database:

    SRPS_TEST_DB_HOST  SRPS_TEST_DB_PORT  SRPS_TEST_DB_USER  SRPS_TEST_DB_PASSWORD

Without them, database tests are skipped and the rest still run.
"""
import os
import pathlib
import secrets

import mysql.connector
import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATABASE_DIR = ROOT / 'database'
TEST_DB_PREFIX = 'srps_test_'
SCRIPT_DB_NAME = 'student_result_db'  # name hardcoded in the shipped SQL scripts


def assert_test_database(name):
    """The only gate between a test and a destructive statement."""
    assert name.startswith(TEST_DB_PREFIX), f'refusing to touch non-test database {name!r}'


def run_script(connection, path, db_name):
    """Run a shipped SQL script against `db_name` instead of its hardcoded name."""
    assert_test_database(db_name)
    text = pathlib.Path(path).read_text(encoding='utf-8').replace(SCRIPT_DB_NAME, db_name)
    cursor = connection.cursor()
    for result in cursor.execute(text, multi=True):
        if result.with_rows:
            result.fetchall()
    connection.commit()
    cursor.close()


@pytest.fixture(scope='session')
def server():
    names = ['HOST', 'PORT', 'USER', 'PASSWORD']
    values = {n: os.getenv(f'SRPS_TEST_DB_{n}') for n in names}
    missing = [f'SRPS_TEST_DB_{n}' for n, v in values.items() if not v]
    if missing:
        pytest.skip('database tests need ' + ', '.join(missing))
    return {
        'host': values['HOST'],
        'port': int(values['PORT']),
        'user': values['USER'],
        'password': values['PASSWORD'],
    }


@pytest.fixture(scope='session')
def admin_connection(server):
    connection = mysql.connector.connect(**server, autocommit=True)
    yield connection
    connection.close()


def _create_database(admin_connection):
    name = TEST_DB_PREFIX + secrets.token_hex(4)
    cursor = admin_connection.cursor()
    cursor.execute(f'CREATE DATABASE `{name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci')
    cursor.close()
    return name


def _drop_database(admin_connection, name):
    assert_test_database(name)
    cursor = admin_connection.cursor()
    cursor.execute(f'DROP DATABASE IF EXISTS `{name}`')
    cursor.close()


@pytest.fixture
def empty_db(admin_connection, server):
    """A brand-new empty database and a connection to it."""
    name = _create_database(admin_connection)
    connection = mysql.connector.connect(**server, database=name)
    yield name, connection
    connection.close()
    _drop_database(admin_connection, name)


# ---- a fully migrated database and an app wired to it ----------------------

TEST_SECRET_KEY = 'test-only-secret-key-0123456789-abcdefghij'


def app_settings(server, db_name):
    return {
        'SECRET_KEY': TEST_SECRET_KEY,
        'DB_HOST': server['host'],
        'DB_PORT': str(server['port']),
        'DB_USER': server['user'],
        'DB_PASSWORD': server['password'],
        'DB_NAME': db_name,
    }


@pytest.fixture(scope='session')
def migrated_db(admin_connection, server):
    """One database for the whole run: new-install path, then every migration."""
    from services.migrations import apply_pending

    name = _create_database(admin_connection)
    connection = mysql.connector.connect(**server, database=name)
    for script in ('schema.sql', 'migration_add_assessments.sql'):
        run_script(connection, DATABASE_DIR / script, name)
    apply_pending(connection)
    connection.close()
    yield name
    _drop_database(admin_connection, name)


@pytest.fixture
def clean_db(migrated_db, server):
    """The migrated database with every row removed except the 6 stock assessments."""
    assert_test_database(migrated_db)
    connection = mysql.connector.connect(**server, database=migrated_db)
    cursor = connection.cursor()
    cursor.execute('SET FOREIGN_KEY_CHECKS = 0')
    cursor.execute('SHOW TABLES')
    for (table,) in cursor.fetchall():
        if table != 'schema_migrations':
            cursor.execute(f'TRUNCATE TABLE `{table}`')
    cursor.execute('SET FOREIGN_KEY_CHECKS = 1')
    connection.commit()
    run_script(connection, DATABASE_DIR / 'migration_add_assessments.sql', migrated_db)
    cursor.close()
    connection.close()
    return migrated_db


@pytest.fixture
def app(clean_db, server):
    from app import create_app

    flask_app = create_app(app_settings(server, clean_db), testing=True)
    flask_app.config['PROPAGATE_EXCEPTIONS'] = False  # let error pages render in tests
    return flask_app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def ctx(app):
    """An application context, for tests that call services directly."""
    with app.app_context():
        yield app


@pytest.fixture
def sign_in(app):
    """Factory: create an account with the given role and return a signed-in browser for it."""
    import itertools
    from types import SimpleNamespace

    from tests.factories import make_faculty, make_student, make_user
    from tests.helpers import login

    counter = itertools.count(1)

    def _sign_in(role, **links):
        n = next(counter)
        username = f'{role}{n}'
        with app.app_context():
            if role == 'student' and 'student_id' not in links:
                links['student_id'] = make_student(f'S{n:04}', f'Student {n}')
            if role == 'faculty' and 'faculty_id' not in links:
                links['faculty_id'] = make_faculty(f'F{n:04}', f'Faculty {n}')
            user_id = make_user(username, role, **links)
        browser = app.test_client()
        assert login(browser, username).status_code == 302
        return SimpleNamespace(client=browser, user_id=user_id, username=username,
                               student_id=links.get('student_id'), faculty_id=links.get('faculty_id'))

    return _sign_in
