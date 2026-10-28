import pytest

from app import create_app
from db import (DatabaseUnavailable, execute_query, execute_update, is_duplicate_error,
                transaction)
from tests.conftest import app_settings

INSERT_STUDENT = ("INSERT INTO students (registration_number, full_name, semester) "
                  "VALUES (%s, %s, %s)")


def test_update_then_query_roundtrip(app):
    with app.app_context():
        new_id = execute_update(INSERT_STUDENT, ('R1', 'Ria', 2))
        rows = execute_query('SELECT full_name FROM students WHERE student_id = %s', (new_id,))
    assert rows == [{'full_name': 'Ria'}]


def test_transaction_commits_every_statement_together(app):
    with app.app_context():
        with transaction() as cursor:
            cursor.execute(INSERT_STUDENT, ('R1', 'Ria', 2))
            cursor.execute(INSERT_STUDENT, ('R2', 'Raj', 2))
        count = execute_query('SELECT COUNT(*) AS n FROM students')[0]['n']
    assert count == 2


def test_transaction_rolls_everything_back_when_one_statement_fails(app):
    with app.app_context():
        with pytest.raises(Exception) as exc:
            with transaction() as cursor:
                cursor.execute(INSERT_STUDENT, ('R1', 'Ria', 2))
                cursor.execute(INSERT_STUDENT, ('R1', 'Duplicate', 2))
        count = execute_query('SELECT COUNT(*) AS n FROM students')[0]['n']
    assert is_duplicate_error(exc.value)
    assert count == 0


def test_is_duplicate_error_is_false_for_other_errors(app):
    with app.app_context():
        with pytest.raises(Exception) as exc:
            execute_update(INSERT_STUDENT, ('R9', 'Bad Semester', 99))  # CHECK constraint
    assert not is_duplicate_error(exc.value)


def test_unreachable_database_raises_a_friendly_error_that_leaks_nothing(server, clean_db):
    settings = app_settings(server, clean_db)
    settings['DB_PORT'] = '1'  # nothing listens here
    unreachable = create_app(settings, testing=True)
    with unreachable.app_context():
        with pytest.raises(DatabaseUnavailable) as exc:
            execute_query('SELECT 1')
    message = str(exc.value)
    assert 'MySQL' in message
    assert settings['DB_PASSWORD'] not in message
    assert settings['DB_USER'] not in message


def test_foreign_key_errors_are_recognised(app):
    from db import is_missing_reference_error, is_referenced_error
    with app.app_context():
        student = execute_update(INSERT_STUDENT, ('R1', 'Ria', 2))
        execute_update("INSERT INTO faculty (employee_id, full_name) VALUES ('F1', 'Fac')")
        execute_update("INSERT INTO users (username, password_hash, role, student_id) "
                       "VALUES ('ria', 'h', 'student', %s)", (student,))
        with pytest.raises(Exception) as referenced:
            execute_update('DELETE FROM students WHERE student_id = %s', (student,))
        with pytest.raises(Exception) as missing:
            execute_update("INSERT INTO marks (student_id, subject_id, exam_id, marks_obtained, "
                           "maximum_marks) VALUES (999, 999, 999, 1, 10)")
    assert is_referenced_error(referenced.value) and not is_missing_reference_error(referenced.value)
    assert is_missing_reference_error(missing.value) and not is_referenced_error(missing.value)
