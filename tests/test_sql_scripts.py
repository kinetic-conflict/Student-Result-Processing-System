import re

import pytest

from tests.conftest import DATABASE_DIR, run_script
from tests.helpers import SETUP_ORDER, apply_setup, table_counts

SEED_FILES = ['seed.sql', 'seed_vit_students.sql']
ALL_SCRIPTS = SETUP_ORDER + ['queries.sql', 'verification.sql']


def code_only(name, keep_strings=False):
    """Script text without `--` comments and, by default, without string literals."""
    text = (DATABASE_DIR / name).read_text(encoding='utf-8')
    text = '\n'.join(re.sub(r'--.*$', '', line) for line in text.splitlines())
    return text if keep_strings else re.sub(r"'[^']*'", "''", text)


@pytest.mark.parametrize('name', ALL_SCRIPTS)
def test_no_shipped_script_can_destroy_data(name):
    assert not re.search(r'\b(DROP|TRUNCATE)\b|\bDELETE\s+FROM\b', code_only(name), re.IGNORECASE)


@pytest.mark.parametrize('name', ['queries.sql', 'verification.sql'])
def test_reference_scripts_are_read_only(name):
    assert not re.search(r'\b(INSERT|UPDATE|ALTER|CREATE|REPLACE)\b', code_only(name), re.IGNORECASE)


@pytest.mark.parametrize('name', SEED_FILES)
def test_seed_files_create_no_accounts_and_hold_no_secrets(name):
    text = code_only(name, keep_strings=True)
    assert not re.search(r'INTO\s+users', text, re.IGNORECASE)
    assert 'password' not in text.lower()


@pytest.mark.parametrize('name', SEED_FILES)
def test_seed_files_are_labelled_synthetic_and_avoid_real_email_domains(name):
    raw = (DATABASE_DIR / name).read_text(encoding='utf-8')
    assert 'SYNTHETIC' in raw
    assert not re.search(r'vit\.edu|vit\.ac\.in|vitstudent', raw, re.IGNORECASE)


def test_setup_scripts_apply_in_documented_order(empty_db):
    name, connection = empty_db
    apply_setup(connection, name)
    assert table_counts(connection) == {
        'students': 33, 'subjects': 38, 'examinations': 6,
        'marks': 28, 'assessments': 6, 'assessment_marks': 28,
    }


def test_setup_scripts_can_be_run_again_without_changing_anything(empty_db):
    name, connection = empty_db
    apply_setup(connection, name)
    before = table_counts(connection)
    apply_setup(connection, name)
    assert table_counts(connection) == before


def test_rerunning_schema_keeps_existing_rows(empty_db):
    name, connection = empty_db
    apply_setup(connection, name)
    cursor = connection.cursor()
    cursor.execute(
        "INSERT INTO students (registration_number, full_name, semester) "
        "VALUES ('KEEP001', 'Keep Me', 2)"
    )
    connection.commit()
    run_script(connection, DATABASE_DIR / 'schema.sql', name)
    cursor.execute("SELECT full_name FROM students WHERE registration_number = 'KEEP001'")
    assert cursor.fetchone() == ('Keep Me',)
    cursor.close()


@pytest.mark.parametrize('name', ['queries.sql', 'verification.sql'])
def test_reference_scripts_run_clean_and_leave_data_untouched(empty_db, name):
    db_name, connection = empty_db
    apply_setup(connection, db_name)
    cursor = connection.cursor()
    cursor.execute("SELECT email FROM students WHERE student_id = 1")
    email_before = cursor.fetchone()[0]
    cursor.execute("SELECT marks_obtained FROM marks WHERE mark_id = 1")
    mark_before = cursor.fetchone()[0]
    before = table_counts(connection)

    run_script(connection, DATABASE_DIR / name, db_name)

    cursor.execute("SELECT email FROM students WHERE student_id = 1")
    assert cursor.fetchone()[0] == email_before
    cursor.execute("SELECT marks_obtained FROM marks WHERE mark_id = 1")
    assert cursor.fetchone()[0] == mark_before
    assert table_counts(connection) == before
    cursor.close()


def test_seeded_academic_years_are_consecutive_years(empty_db):
    name, connection = empty_db
    apply_setup(connection, name)
    cursor = connection.cursor()
    cursor.execute("SELECT registration_number, academic_year FROM students")
    for registration, year in cursor.fetchall():
        start, end = year.split('-')
        assert int(end) == int(start) + 1, registration
    cursor.close()
