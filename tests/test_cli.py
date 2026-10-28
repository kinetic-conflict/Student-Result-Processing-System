import pytest

from app import create_app
from db import execute_query
from services.migrations import pending_migrations
from tests.conftest import app_settings
from tests.helpers import BASE_SCHEMA, apply_scripts

GOOD_PASSWORD = 'Str0ng-Secret-Pass'


def run(app, *args, input=None):
    return app.test_cli_runner().invoke(args=list(args), input=input)


def users(app):
    with app.app_context():
        return execute_query('SELECT * FROM users')


def test_create_admin_stores_a_hash_and_never_prints_the_password(app):
    result = run(app, 'create-admin', '--username', 'boss',
                 input=f'{GOOD_PASSWORD}\n{GOOD_PASSWORD}\n')
    assert result.exit_code == 0, result.output
    assert GOOD_PASSWORD not in result.output
    (row,) = users(app)
    assert row['username'] == 'boss' and row['role'] == 'admin'
    assert row['password_hash'] != GOOD_PASSWORD
    assert row['must_change_password'] == 0   # the admin just chose it themselves


def test_create_admin_rejects_a_weak_password(app):
    result = run(app, 'create-admin', '--username', 'boss', input='short\nshort\n')
    assert result.exit_code != 0
    assert 'at least 10' in result.output
    assert users(app) == []


def test_create_admin_needs_the_password_typed_twice_the_same(app):
    result = run(app, 'create-admin', '--username', 'boss',
                 input=f'{GOOD_PASSWORD}\nsomething-else-entirely\n')
    assert result.exit_code != 0
    assert 'do not match' in result.output
    assert users(app) == []


def test_create_admin_refuses_an_existing_username(app):
    run(app, 'create-admin', '--username', 'boss', input=f'{GOOD_PASSWORD}\n{GOOD_PASSWORD}\n')
    result = run(app, 'create-admin', '--username', 'BOSS',
                 input=f'{GOOD_PASSWORD}\n{GOOD_PASSWORD}\n')
    assert result.exit_code != 0
    assert 'already in use' in result.output
    assert len(users(app)) == 1


@pytest.fixture
def unmigrated_app(empty_db, server):
    name, connection = empty_db
    apply_scripts(connection, name, BASE_SCHEMA)
    return create_app(app_settings(server, name), testing=True), connection


def test_migrate_asks_about_a_backup_and_stops_on_no(unmigrated_app):
    app, connection = unmigrated_app
    result = run(app, 'migrate', input='n\n')
    assert result.exit_code != 0
    assert 'backed up' in result.output
    assert len(pending_migrations(connection)) == 3


def test_migrate_applies_everything_with_yes_and_is_then_a_no_op(unmigrated_app):
    app, connection = unmigrated_app
    result = run(app, 'migrate', '--yes')
    assert result.exit_code == 0, result.output
    for version in ('001_faculty', '002_accounts', '003_audit_log'):
        assert version in result.output
    assert pending_migrations(connection) == []
    again = run(app, 'migrate', '--yes')
    assert again.exit_code == 0 and 'up to date' in again.output


def test_migrate_explains_a_missing_base_schema(empty_db, server):
    name, _ = empty_db
    app = create_app(app_settings(server, name), testing=True)
    result = run(app, 'migrate', '--yes')
    assert result.exit_code != 0
    assert 'schema.sql' in result.output


def test_commands_report_an_unreachable_database_plainly(server, clean_db):
    settings = dict(app_settings(server, clean_db), DB_PORT='1')
    result = run(create_app(settings, testing=True), 'migrate', '--yes')
    assert result.exit_code != 0
    assert 'Could not connect to the MySQL database' in result.output
