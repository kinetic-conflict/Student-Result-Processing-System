"""database/integrity_checks.sql: read-only checks that name every problem they find."""
import pytest

from tests.conftest import DATABASE_DIR, SCRIPT_DB_NAME, assert_test_database
from tests.helpers import apply_setup, table_counts


def problems(connection, db_name):
    """Run the script; return the first column of every result set that reports a problem."""
    assert_test_database(db_name)
    text = (DATABASE_DIR / 'integrity_checks.sql').read_text(encoding='utf-8').replace(SCRIPT_DB_NAME, db_name)
    cursor = connection.cursor()
    found = []
    for result in cursor.execute(text, multi=True):
        if result.with_rows:
            rows = result.fetchall()
            if result.column_names[0] == 'problem':
                found += [row[0] for row in rows]
    cursor.close()
    return found


def change(connection, sql):
    cursor = connection.cursor()
    cursor.execute(sql)
    connection.commit()
    cursor.close()


@pytest.fixture
def seeded(empty_db):
    name, connection = empty_db
    apply_setup(connection, name)
    return name, connection


def test_the_sample_database_is_healthy(seeded):
    name, connection = seeded
    assert problems(connection, name) == []


def test_running_the_checks_changes_nothing(seeded):
    name, connection = seeded
    before = table_counts(connection)
    problems(connection, name)
    assert table_counts(connection) == before


def test_weights_that_do_not_total_100_are_reported(seeded):
    name, connection = seeded
    change(connection, "UPDATE assessments SET weight_percentage = 20 WHERE assessment_code = 'CAT1'")
    (finding,) = problems(connection, name)
    assert 'weights total 105' in finding


def test_a_missing_assessment_definition_is_reported(seeded):
    name, connection = seeded                    # a throwaway database, so this delete is safe here
    change(connection, 'DELETE FROM assessments')
    assert any('No assessment components' in finding for finding in problems(connection, name))


def test_a_mark_above_a_lowered_maximum_is_reported(seeded):
    name, connection = seeded
    change(connection, "UPDATE assessments SET maximum_marks = 60 WHERE assessment_code = 'ENDSEM'")
    findings = problems(connection, name)
    assert findings and all('above its maximum' in f for f in findings)
    assert any('2024CS001' in f and 'ENDSEM' in f for f in findings)


def test_a_duplicated_examination_is_reported(seeded):
    name, connection = seeded
    change(connection, "INSERT INTO examinations (exam_name, academic_year, semester) "
                       "VALUES ('end semester examination', '2024-2025', 3)")
    (finding,) = problems(connection, name)
    assert 'Duplicate examination' in finding and '2 rows' in finding


def test_an_examination_in_another_semester_than_its_subject_is_flagged_for_review(seeded):
    name, connection = seeded
    change(connection, "UPDATE examinations SET semester = 4 WHERE exam_name = 'End Semester Examination'")
    findings = problems(connection, name)
    assert len(findings) == 28 and all(f.startswith('Review:') for f in findings)


def test_assessment_marks_outside_the_students_semester_are_flagged_for_review(seeded):
    name, connection = seeded
    change(connection, "UPDATE students SET semester = 5 WHERE registration_number = '2024CS001'")
    findings = problems(connection, name)
    assert findings and all(f.startswith('Review:') and '2024CS001' in f for f in findings)
