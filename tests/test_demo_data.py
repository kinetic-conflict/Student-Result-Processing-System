"""The sample-marks command: explicit, deterministic, and limited to the synthetic students."""
from decimal import Decimal

import pytest

from db import execute_query
from services import assessment_config, auth_service, demo_data, result_queries
from services.result_service import calculate_student_result_with_assessments
from tests.factories import make_exam, make_legacy_mark, make_student, make_subject, record_mark

SYNTHETIC = '@students.example'


def run(app, *args, input=None):
    return app.test_cli_runner().invoke(args=list(args), input=input)


def marks_table(app):
    with app.app_context():
        return execute_query(
            'SELECT s.registration_number AS reg, a.assessment_code AS code, am.marks_obtained AS marks '
            'FROM assessment_marks am JOIN students s ON s.student_id = am.student_id '
            'JOIN assessments a ON a.assessment_id = am.assessment_id '
            'ORDER BY s.registration_number, a.assessment_id')


def by_student(rows):
    table = {}
    for row in rows:
        table.setdefault(row['reg'], {})[row['code']] = row['marks']
    return table


@pytest.fixture
def roster(app):
    """Ten synthetic students (D001..D010) with one 80/100 examination mark each, plus a real student."""
    with app.app_context():
        subject, exam = make_subject('CS301', 'Algorithms', 3), make_exam()
        for n in range(1, 11):
            student = make_student(f'D{n:03}', f'Demo {n}', 3, email=f'demo{n}{SYNTHETIC}')
            make_legacy_mark(student, subject, exam, 80, 100)
        real = make_student('R001', 'Real Person', 3, email='real.person@example.org')
        make_legacy_mark(real, subject, exam, 91, 100)
    return app


# ---- the numbers ------------------------------------------------------------

def test_a_roster_entry_gets_the_expected_component_marks(roster):
    run(roster, 'seed-demo', '--yes')
    first = by_student(marks_table(roster))['D001']
    assert {code: float(value) for code, value in first.items()} == {
        'CAT1': 38.0, 'CAT2': 41.0, 'CAT3': 39.5, 'ASSIGN': 43.0, 'PROJECT': 83.0, 'ENDSEM': 80.0}


def test_the_end_semester_component_matches_the_examination_mark(roster):
    run(roster, 'seed-demo', '--yes')
    table = by_student(marks_table(roster))
    assert all(marks['ENDSEM'] == Decimal('80') for reg, marks in table.items() if 'ENDSEM' in marks)


def test_the_same_input_always_gives_the_same_marks(roster):
    with roster.app_context():
        first, second = demo_data.plan(), demo_data.plan()
    assert first.rows == second.rows and first.rows


def test_a_complete_sample_record_is_graded_by_the_existing_rules(roster):
    run(roster, 'seed-demo', '--yes')
    with roster.app_context():
        config = assessment_config.for_calculation(assessment_config.load_config())
    result = calculate_student_result_with_assessments(by_student(marks_table(roster))['D001'], config)
    assert (result['total_weighted_score'], result['grade'], result['status']) == (80.75, 'A', 'Pass')


def test_some_records_are_left_incomplete_and_one_has_a_real_zero(roster):
    run(roster, 'seed-demo', '--yes')
    table = by_student(marks_table(roster))
    assert 'PROJECT' not in table['D007'] and 'ENDSEM' not in table['D007']    # missing: no row at all
    assert table['D010']['ASSIGN'] == Decimal('0')                              # zero: a stored row
    with roster.app_context():
        admin = auth_service.get_user(auth_service.create_user('boss', 'admin', password='Correct-Horse-9',
                                                                must_change_password=False))
        results = {row['registration_number']: row['result']
                   for row in result_queries.weighted_results(admin, per_page=100)['rows']}
    assert results['D007']['status'] == 'Incomplete' and results['D007']['total_weighted_score'] is None
    assert results['D010']['status'] != 'Incomplete'


def test_every_generated_mark_is_in_range_with_at_most_two_decimals(roster):
    with roster.app_context():
        plan = demo_data.plan()
        maximums = {row['assessment_id']: row['max'] for row in assessment_config.load_config()}
    assert plan.rows
    for row in plan.rows:
        assert 0 <= row['value'] <= maximums[row['assessment_id']]
        assert -row['value'].as_tuple().exponent <= 2


# ---- safety -----------------------------------------------------------------

def test_planning_writes_nothing(roster):
    with roster.app_context():
        demo_data.plan()
    assert marks_table(roster) == []


def test_only_synthetic_students_get_marks(roster):
    run(roster, 'seed-demo', '--yes')
    assert 'R001' not in by_student(marks_table(roster))


def test_existing_marks_are_never_changed_or_removed(roster):
    with roster.app_context():
        student = execute_query("SELECT student_id FROM students WHERE registration_number = 'D001'")[0]
        subject = execute_query('SELECT subject_id FROM subjects')[0]
        record_mark(student['student_id'], subject['subject_id'], 'CAT1', 12)
    run(roster, 'seed-demo', '--yes')
    assert by_student(marks_table(roster))['D001']['CAT1'] == Decimal('12')


def test_running_it_twice_adds_nothing_the_second_time(roster):
    run(roster, 'seed-demo', '--yes')
    before = marks_table(roster)
    result = run(roster, 'seed-demo', '--yes')
    assert result.exit_code == 0 and 'already' in result.output
    assert marks_table(roster) == before


def test_the_command_asks_first_and_changes_nothing_on_no(roster):
    result = run(roster, 'seed-demo', input='n\n')
    assert result.exit_code != 0
    assert marks_table(roster) == []


def test_the_command_states_what_it_will_do(roster):
    result = run(roster, 'seed-demo', input='n\n')
    assert 'synthetic' in result.output and '10 students' in result.output
    assert 'never changed' in result.output


def test_without_sample_students_there_is_nothing_to_do(app):
    result = run(app, 'seed-demo', '--yes')
    assert result.exit_code == 0 and 'Nothing to add' in result.output
    assert marks_table(app) == []


def test_nothing_is_seeded_just_by_starting_the_app_or_loading_the_roster(roster):
    assert marks_table(roster) == []


def test_the_run_is_written_to_the_audit_log(roster):
    run(roster, 'seed-demo', '--yes')
    with roster.app_context():
        (entry,) = execute_query("SELECT * FROM audit_log WHERE action = 'demo_data.seed'")
    assert entry['user_id'] is None and 'synthetic' in entry['detail']
