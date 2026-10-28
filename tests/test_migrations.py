import re

import mysql.connector
import pytest

from services.migrations import MIGRATIONS_DIR, MigrationError, apply_pending, pending_migrations
from tests.helpers import BASE_SCHEMA, apply_scripts, apply_setup, table_counts

EXPECTED_VERSIONS = ['001_faculty', '002_accounts', '003_audit_log']


@pytest.fixture
def base_db(empty_db):
    name, connection = empty_db
    apply_scripts(connection, name, BASE_SCHEMA)
    return name, connection


def column_names(connection, table):
    cursor = connection.cursor()
    cursor.execute(f'SHOW COLUMNS FROM {table}')
    names = {row[0] for row in cursor.fetchall()}
    cursor.close()
    return names


def test_migration_files_are_numbered_and_never_destructive():
    files = sorted(p.name for p in MIGRATIONS_DIR.glob('*.sql'))
    assert [f[:-4] for f in files] == EXPECTED_VERSIONS
    for path in MIGRATIONS_DIR.glob('*.sql'):
        code = '\n'.join(re.sub(r'--.*$', '', line) for line in path.read_text().splitlines())
        code = re.sub(r"'[^']*'", "''", code)
        assert not re.search(r'\b(DROP|TRUNCATE)\b|\bDELETE\s+FROM\b', code, re.IGNORECASE), path.name


def test_pending_lists_every_migration_in_order_on_a_fresh_base(base_db):
    _, connection = base_db
    assert [p.stem for p in pending_migrations(connection)] == EXPECTED_VERSIONS


def test_apply_creates_the_account_faculty_and_audit_structures(base_db):
    _, connection = base_db
    assert apply_pending(connection) == EXPECTED_VERSIONS
    assert {'email', 'is_active', 'must_change_password', 'session_version',
            'student_id', 'faculty_id', 'last_login_at'} <= column_names(connection, 'users')
    assert {'employee_id', 'full_name', 'is_active'} <= column_names(connection, 'faculty')
    assert {'faculty_id', 'subject_id'} <= column_names(connection, 'faculty_assignments')
    assert {'action', 'entity', 'user_id', 'created_at'} <= column_names(connection, 'audit_log')


def test_second_run_applies_nothing(base_db):
    _, connection = base_db
    apply_pending(connection)
    assert apply_pending(connection) == []
    assert pending_migrations(connection) == []


def test_existing_rows_survive_the_migration_unchanged(empty_db):
    name, connection = empty_db
    apply_setup(connection, name)
    cursor = connection.cursor()
    cursor.execute("INSERT INTO users (username, password_hash, role) VALUES ('legacy', 'opaque-hash-value', 'admin')")
    connection.commit()
    cursor.execute('SELECT * FROM students ORDER BY student_id')
    students_before = cursor.fetchall()
    cursor.execute('SELECT * FROM marks ORDER BY mark_id')
    marks_before = cursor.fetchall()
    counts_before = table_counts(connection)

    apply_pending(connection)

    assert table_counts(connection) == counts_before
    cursor.execute('SELECT * FROM students ORDER BY student_id')
    assert cursor.fetchall() == students_before
    cursor.execute('SELECT * FROM marks ORDER BY mark_id')
    assert cursor.fetchall() == marks_before
    cursor.execute("SELECT username, password_hash, role, is_active, must_change_password, "
                   "student_id, faculty_id FROM users WHERE username = 'legacy'")
    assert cursor.fetchone() == ('legacy', 'opaque-hash-value', 'admin', 1, 0, None, None)
    cursor.close()


def test_users_table_rejects_unknown_roles_and_mismatched_links(base_db):
    _, connection = base_db
    apply_pending(connection)
    cursor = connection.cursor()
    cursor.execute("INSERT INTO students (registration_number, full_name, semester) VALUES ('S1', 'Stu', 1)")
    student_id = cursor.lastrowid
    bad_rows = [
        ("u1", 'superuser', None),       # role outside the allowed set
        ("u2", 'student', None),         # student account without a student record
        ("u3", 'faculty', None),         # faculty account without a faculty record
        ("u4", 'admin', student_id),     # admin pointing at a student record
    ]
    for username, role, student in bad_rows:
        with pytest.raises(mysql.connector.Error):
            cursor.execute(
                'INSERT INTO users (username, password_hash, role, student_id) VALUES (%s, %s, %s, %s)',
                (username, 'h', role, student))
    cursor.execute("INSERT INTO users (username, password_hash, role, student_id) VALUES ('ok', 'h', 'student', %s)",
                   (student_id,))
    with pytest.raises(mysql.connector.Error):  # one account per student record
        cursor.execute("INSERT INTO users (username, password_hash, role, student_id) VALUES ('dup', 'h', 'student', %s)",
                       (student_id,))
    connection.rollback()
    cursor.close()


def test_missing_base_schema_is_reported_with_the_fix(empty_db):
    _, connection = empty_db
    with pytest.raises(MigrationError) as exc:
        apply_pending(connection)
    assert 'schema.sql' in str(exc.value)


def test_failed_migration_is_not_recorded_and_stops_the_run(base_db, tmp_path):
    _, connection = base_db
    (tmp_path / '001_ok.sql').write_text('CREATE TABLE IF NOT EXISTS scratch_ok (id INT PRIMARY KEY);')
    (tmp_path / '002_bad.sql').write_text('ALTER TABLE no_such_table ADD COLUMN x INT;')
    (tmp_path / '003_never.sql').write_text('CREATE TABLE IF NOT EXISTS scratch_never (id INT PRIMARY KEY);')

    with pytest.raises(MigrationError, match='002_bad'):
        apply_pending(connection, tmp_path)

    assert [p.stem for p in pending_migrations(connection, tmp_path)] == ['002_bad', '003_never']
    cursor = connection.cursor()
    cursor.execute("SHOW TABLES LIKE 'scratch_never'")
    assert cursor.fetchall() == []
    cursor.close()
