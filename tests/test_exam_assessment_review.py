"""Examinations and assessment components: no duplicates, zero is not missing, the two stay separate."""
import re
from decimal import Decimal

import pytest

from db import execute_query
from services import assessment_config, auth_service, exam_results, marks_service
from services.result_service import calculate_student_result_with_assessments
from tests.factories import (make_exam, make_legacy_mark, make_student, make_subject, make_user,
                             record_all_marks)
from tests.helpers import post

EXAM_FORM = {'exam_name': 'Mid Term', 'academic_year': '2024-2025', 'semester': '3',
             'exam_date': '2024-10-15'}
FULL = {'CAT1': 42, 'CAT2': 38, 'CAT3': 45, 'ASSIGN': 40, 'PROJECT': 85, 'ENDSEM': 78}


@pytest.fixture
def admin(sign_in):
    return sign_in('admin')


def rows(app, sql, params=()):
    with app.app_context():
        return execute_query(sql, params)


def result_for(marks):
    config = assessment_config.for_calculation(assessment_config.load_config())
    return calculate_student_result_with_assessments(marks, config)


# ---- examinations are not duplicated ----------------------------------------

def test_the_same_examination_cannot_be_added_twice(app, admin):
    assert post(admin.client, '/examinations/add', EXAM_FORM).status_code == 302
    again = post(admin.client, '/examinations/add', EXAM_FORM)
    assert again.status_code == 200 and b'already exists' in again.data
    assert len(rows(app, 'SELECT 1 FROM examinations')) == 1


def test_case_and_spacing_do_not_make_a_new_examination(app, admin):
    post(admin.client, '/examinations/add', EXAM_FORM)
    again = post(admin.client, '/examinations/add', dict(EXAM_FORM, exam_name='  mid term '))
    assert again.status_code == 200 and b'already exists' in again.data
    assert len(rows(app, 'SELECT 1 FROM examinations')) == 1


def test_another_year_or_semester_is_a_different_examination(app, admin):
    post(admin.client, '/examinations/add', EXAM_FORM)
    assert post(admin.client, '/examinations/add',
                dict(EXAM_FORM, academic_year='2025-2026')).status_code == 302
    assert post(admin.client, '/examinations/add', dict(EXAM_FORM, semester='4')).status_code == 302
    assert len(rows(app, 'SELECT 1 FROM examinations')) == 3


def test_editing_cannot_turn_one_examination_into_another(app, admin):
    post(admin.client, '/examinations/add', EXAM_FORM)
    post(admin.client, '/examinations/add', dict(EXAM_FORM, exam_name='End Term'))
    end = rows(app, "SELECT exam_id FROM examinations WHERE exam_name = 'End Term'")[0]['exam_id']
    clash = post(admin.client, f'/examinations/{end}/edit', EXAM_FORM)
    assert clash.status_code == 200 and b'already exists' in clash.data
    assert rows(app, 'SELECT exam_name FROM examinations WHERE exam_id = %s', (end,))[0]['exam_name'] == 'End Term'


def test_an_examination_can_be_saved_again_with_only_its_date_changed(app, admin):
    post(admin.client, '/examinations/add', EXAM_FORM)
    exam = rows(app, 'SELECT exam_id FROM examinations')[0]['exam_id']
    assert post(admin.client, f'/examinations/{exam}/edit',
                dict(EXAM_FORM, exam_date='2024-10-20')).status_code == 302
    assert str(rows(app, 'SELECT exam_date FROM examinations')[0]['exam_date']) == '2024-10-20'


# ---- zero is a mark, blank is not -------------------------------------------

@pytest.fixture
def pair(ctx):
    student, subject = make_student('S001', 'Ann', 3), make_subject('CS301', 'Algorithms', 3)
    boss = auth_service.get_user(make_user('boss', 'admin'))
    return student, subject, boss


def test_a_zero_is_stored_and_counts_as_entered(pair):
    student, subject, boss = pair
    marks_service.save_marks(boss, subject, {student: {code: Decimal(value) for code, value in
                                                      dict(FULL, CAT1=0).items()}})
    stored = {r['code']: r['marks'] for r in execute_query(
        'SELECT a.assessment_code AS code, am.marks_obtained AS marks FROM assessment_marks am '
        'JOIN assessments a ON a.assessment_id = am.assessment_id')}
    assert stored['CAT1'] == Decimal('0')
    result = result_for(stored)
    cat1 = result['assessment_breakdown'][0]
    assert (cat1['marks_obtained'], cat1['weighted_score']) == (0.0, 0.0)
    assert result['status'] != 'Incomplete'


def test_a_blank_never_becomes_a_zero(pair):
    student, subject, boss = pair
    marks_service.save_marks(boss, subject, {student: {'CAT1': Decimal(40), 'CAT2': None}})
    codes = {r['code'] for r in execute_query(
        'SELECT a.assessment_code AS code FROM assessment_marks am '
        'JOIN assessments a ON a.assessment_id = am.assessment_id')}
    assert codes == {'CAT1'}
    assert result_for({'CAT1': Decimal(40)})['status'] == 'Incomplete'


def test_the_grid_shows_a_zero_as_0_and_a_missing_mark_as_empty(app, admin):
    with app.app_context():
        student, subject = make_student('S001', 'Ann', 3), make_subject('CS301', 'Algorithms', 3)
        record_all_marks(student, subject, {'CAT1': 0})
    html = admin.client.get(f'/assessments/subjects/{subject}').data.decode()
    assert re.search(rf'name="m_{student}_CAT1"[^>]*value="0"', html)
    assert re.search(rf'name="m_{student}_CAT2"[^>]*value=""', html)


# ---- the two kinds of mark stay separate ------------------------------------

def test_examination_marks_and_assessment_marks_do_not_touch_each_other(app, admin):
    with app.app_context():
        student, subject = make_student('S001', 'Ann', 3), make_subject('CS301', 'Algorithms', 3)
        exam = make_exam()
        legacy = make_legacy_mark(student, subject, exam, 70, 100)
        record_all_marks(student, subject, FULL)
    legacy_before = rows(app, 'SELECT * FROM marks')
    post(admin.client, f'/assessments/subjects/{subject}', {f'm_{student}_CAT1': '10'})
    assert rows(app, 'SELECT * FROM marks') == legacy_before

    assessment_before = rows(app, 'SELECT * FROM assessment_marks ORDER BY 1')
    post(admin.client, f'/marks/{legacy}/edit', {'marks_obtained': '55', 'maximum_marks': '100'})
    assert rows(app, 'SELECT * FROM assessment_marks ORDER BY 1') == assessment_before


def test_editing_an_examination_mark_changes_that_examinations_result(app, admin):
    with app.app_context():
        student, subject = make_student('S001', 'Ann', 3), make_subject('CS301', 'Algorithms', 3)
        mark = make_legacy_mark(student, subject, make_exam(), 38, 100)
    with app.app_context():
        assert exam_results.student_exam_results(student)[0]['result']['status'] == 'Fail'
    post(admin.client, f'/marks/{mark}/edit', {'marks_obtained': '45', 'maximum_marks': '100'})
    with app.app_context():
        result = exam_results.student_exam_results(student)[0]['result']
    assert (result['overall_percentage'], result['status']) == (45.0, 'Pass')


@pytest.mark.parametrize('obtained, maximum, message', [
    ('101', '100', b'cannot exceed'), ('-1', '100', b'at least 0'), ('5', '0', b'greater than 0'),
    ('5.555', '100', b'decimal places'), ('x', '100', b'must be a number'),
])
def test_examination_mark_values_are_validated(app, admin, obtained, maximum, message):
    with app.app_context():
        student, subject, exam = (make_student('S001', 'Ann', 3), make_subject('CS301', 'Algorithms', 3),
                                  make_exam())
    response = post(admin.client, '/marks/add', {
        'student_id': str(student), 'subject_id': str(subject), 'exam_id': str(exam),
        'marks_obtained': obtained, 'maximum_marks': maximum})
    assert response.status_code == 200 and message in response.data
    assert rows(app, 'SELECT 1 FROM marks') == []


def test_an_examination_mark_of_zero_is_allowed(app, admin):
    with app.app_context():
        student, subject, exam = (make_student('S001', 'Ann', 3), make_subject('CS301', 'Algorithms', 3),
                                  make_exam())
    assert post(admin.client, '/marks/add', {
        'student_id': str(student), 'subject_id': str(subject), 'exam_id': str(exam),
        'marks_obtained': '0', 'maximum_marks': '100'}).status_code == 302
    assert rows(app, 'SELECT marks_obtained FROM marks')[0]['marks_obtained'] == Decimal('0')
