from types import SimpleNamespace

import pytest

from db import execute_query
from tests.factories import (assign, make_faculty, make_student, make_subject, record_all_marks,
                             record_mark)
from tests.helpers import csrf, post

FULL = {'CAT1': 42, 'CAT2': 38, 'CAT3': 45, 'ASSIGN': 40, 'PROJECT': 85, 'ENDSEM': 78}


@pytest.fixture
def world(app, sign_in):
    with app.app_context():
        w = SimpleNamespace(
            algo=make_subject('CS301', 'Algorithms', 3),
            db=make_subject('CS302', 'Databases', 3),
            ann=make_student('S001', 'Ann Rao', 3),
            ben=make_student('S002', 'Ben Das', 3),
            cat=make_student('S003', 'Cat Roy', 5),
        )
        first, second = make_faculty('F100', 'Dr First'), make_faculty('F200', 'Dr Second')
        assign(first, w.algo)
        assign(second, w.db)
    w.app = app
    w.admin = sign_in('admin')
    w.teacher = sign_in('faculty', faculty_id=first)
    w.other = sign_in('faculty', faculty_id=second)
    w.ann_user = sign_in('student', student_id=w.ann)
    return w


def stored(world, student, subject):
    with world.app.app_context():
        rows = execute_query(
            'SELECT a.assessment_code AS code, am.marks_obtained AS marks FROM assessment_marks am '
            'JOIN assessments a ON a.assessment_id = am.assessment_id '
            'WHERE am.student_id = %s AND am.subject_id = %s', (student, subject))
    return {row['code']: float(row['marks']) for row in rows}


def seed(world, student, subject, marks):
    with world.app.app_context():
        record_all_marks(student, subject, marks)


def mark_id(world, student, subject, code='CAT1'):
    with world.app.app_context():
        return execute_query(
            'SELECT am.assessment_mark_id AS id FROM assessment_marks am '
            'JOIN assessments a ON a.assessment_id = am.assessment_id '
            'WHERE am.student_id = %s AND am.subject_id = %s AND a.assessment_code = %s',
            (student, subject, code))[0]['id']


# ---- the subject grid -------------------------------------------------------

def test_grid_lists_the_assigned_subjects_cohort_only(world):
    page = world.teacher.client.get(f'/assessments/subjects/{world.algo}')
    assert page.status_code == 200
    assert b'Ann Rao' in page.data and b'Ben Das' in page.data
    assert b'Cat Roy' not in page.data


def test_grid_for_a_subject_someone_else_teaches_is_forbidden(world):
    assert world.teacher.client.get(f'/assessments/subjects/{world.db}').status_code == 403
    assert world.other.client.get(f'/assessments/subjects/{world.algo}').status_code == 403


def test_admin_can_open_any_grid(world):
    assert world.admin.client.get(f'/assessments/subjects/{world.db}').status_code == 200


def test_grid_save_stores_the_marks(world):
    response = post(world.teacher.client, f'/assessments/subjects/{world.algo}', {
        f'm_{world.ann}_CAT1': '40', f'm_{world.ann}_ENDSEM': '77.5', f'm_{world.ben}_CAT1': '35'})
    assert response.status_code == 302
    assert stored(world, world.ann, world.algo) == {'CAT1': 40, 'ENDSEM': 77.5}
    assert stored(world, world.ben, world.algo) == {'CAT1': 35}


def test_grid_ignores_students_outside_the_cohort_even_if_the_form_names_them(world):
    post(world.teacher.client, f'/assessments/subjects/{world.algo}', {
        f'm_{world.ann}_CAT1': '40', f'm_{world.cat}_CAT1': '50'})
    assert stored(world, world.cat, world.algo) == {}
    assert stored(world, world.ann, world.algo) == {'CAT1': 40}


def test_grid_post_to_someone_elses_subject_saves_nothing(world):
    response = post(world.other.client, f'/assessments/subjects/{world.algo}',
                    {f'm_{world.ann}_CAT1': '40'})
    assert response.status_code == 403
    assert stored(world, world.ann, world.algo) == {}


@pytest.mark.parametrize('bad, message', [
    ('abc', b'must be a number'), ('nan', b'must be a number'), ('-1', b'between 0 and 50'),
    ('51', b'between 0 and 50'), ('1.234', b'decimal places'),
])
def test_grid_rejects_bad_numbers_keeps_what_was_typed_and_saves_nothing(world, bad, message):
    response = post(world.teacher.client, f'/assessments/subjects/{world.algo}', {
        f'm_{world.ann}_CAT1': bad, f'm_{world.ben}_CAT1': '35'})
    assert response.status_code == 200
    assert message in response.data
    assert f'value="{bad}"'.encode() in response.data
    assert stored(world, world.ben, world.algo) == {}


def test_grid_post_needs_a_csrf_token(world):
    response = post(world.teacher.client, f'/assessments/subjects/{world.algo}',
                    {f'm_{world.ann}_CAT1': '40', 'csrf_token': None})
    assert response.status_code == 400
    assert stored(world, world.ann, world.algo) == {}


def test_grid_for_an_unknown_subject_is_not_found(world):
    assert world.admin.client.get('/assessments/subjects/99999').status_code == 404


# ---- single-student entry ---------------------------------------------------

def test_admin_enters_marks_for_one_student(world):
    response = post(world.admin.client, '/assessments/enter', {
        'student_id': str(world.ann), 'subject_id': str(world.db),
        'marks_CAT1': '41', 'marks_CAT2': ''})
    assert response.status_code == 302
    assert stored(world, world.ann, world.db) == {'CAT1': 41}


def test_faculty_cannot_enter_marks_outside_their_assignment(world):
    for student, subject in ((world.ann, world.db), (world.cat, world.algo)):
        response = post(world.teacher.client, '/assessments/enter', {
            'student_id': str(student), 'subject_id': str(subject), 'marks_CAT1': '41'})
        assert response.status_code == 403
        assert stored(world, student, subject) == {}


def test_entry_form_only_offers_what_the_user_may_use(world):
    page = world.teacher.client.get('/assessments/enter').data
    assert b'CS301' in page and b'CS302' not in page
    assert b'Ann Rao' in page and b'Cat Roy' not in page


def test_entry_rejects_non_numeric_ids_without_crashing(world):
    response = post(world.admin.client, '/assessments/enter',
                    {'student_id': 'abc', 'subject_id': "1'; DROP TABLE students;--"})
    assert response.status_code == 200
    assert b'Traceback' not in response.data


# ---- editing and deleting one mark ------------------------------------------

def test_faculty_edit_a_mark_in_scope(world):
    seed(world, world.ann, world.algo, FULL)
    target = mark_id(world, world.ann, world.algo)
    assert world.teacher.client.get(f'/assessments/{target}/edit').status_code == 200
    assert post(world.teacher.client, f'/assessments/{target}/edit',
                {'marks_obtained': '44'}).status_code == 302
    assert stored(world, world.ann, world.algo)['CAT1'] == 44
    too_high = post(world.teacher.client, f'/assessments/{target}/edit', {'marks_obtained': '51'})
    assert too_high.status_code == 200 and b'between 0 and 50' in too_high.data
    assert stored(world, world.ann, world.algo)['CAT1'] == 44


def test_faculty_cannot_open_or_change_a_mark_outside_their_scope(world):
    seed(world, world.ann, world.db, FULL)
    target = mark_id(world, world.ann, world.db)
    assert world.teacher.client.get(f'/assessments/{target}/edit').status_code == 403
    assert post(world.teacher.client, f'/assessments/{target}/edit',
                {'marks_obtained': '1'}).status_code == 403
    assert stored(world, world.ann, world.db)['CAT1'] == 42


def test_a_nonexistent_mark_is_forbidden_to_faculty_and_missing_to_admins(world):
    assert world.teacher.client.get('/assessments/99999/edit').status_code == 403
    assert world.admin.client.get('/assessments/99999/edit').status_code == 404


def test_only_admins_delete_marks(world):
    seed(world, world.ann, world.algo, FULL)
    target = mark_id(world, world.ann, world.algo)
    assert post(world.teacher.client, f'/assessments/{target}/delete').status_code == 403
    assert 'CAT1' in stored(world, world.ann, world.algo)
    assert post(world.admin.client, f'/assessments/{target}/delete').status_code == 302
    assert 'CAT1' not in stored(world, world.ann, world.algo)


def test_every_mark_change_lands_in_the_audit_log(world):
    post(world.teacher.client, f'/assessments/subjects/{world.algo}', {f'm_{world.ann}_CAT1': '40'})
    with world.app.app_context():
        (entry,) = execute_query('SELECT * FROM audit_log')
    assert entry['username'] == world.teacher.username and entry['action'] == 'mark.save'


# ---- listings and the calculation page --------------------------------------

def test_mark_list_is_scoped_to_what_the_user_may_see(world):
    seed(world, world.ann, world.algo, FULL)
    seed(world, world.ann, world.db, FULL)
    teacher_page = world.teacher.client.get('/assessments').data
    admin_page = world.admin.client.get('/assessments').data
    assert b'CS301' in teacher_page and b'CS302' not in teacher_page
    assert b'CS301' in admin_page and b'CS302' in admin_page


def test_mark_list_survives_junk_paging_and_filters(world):
    for query in ('?page=abc', '?page=-5', '?subject_id=x', '?student_id=%27', '?page=99999'):
        assert world.admin.client.get('/assessments' + query).status_code == 200, query


def test_filtering_the_list_by_someone_elses_subject_shows_nothing_to_faculty(world):
    seed(world, world.ann, world.db, FULL)
    page = world.teacher.client.get(f'/assessments?subject_id={world.db}').data
    assert b'CS302' not in page


def test_results_listing_shows_totals_and_respects_scope(world):
    seed(world, world.ann, world.algo, FULL)
    seed(world, world.ann, world.db, FULL)
    page = world.teacher.client.get('/assessments/results').data
    assert b'82.0' in page and b'Ann Rao' in page
    assert page.count(b'CS302') == 0
    assert world.ann_user.client.get('/assessments/results').status_code == 403


def test_calculation_page_shows_the_breakdown_in_scope_and_refuses_outside_it(world):
    seed(world, world.ann, world.algo, FULL)
    seed(world, world.ann, world.db, FULL)
    ok = world.teacher.client.get(f'/assessments/calculate?student_id={world.ann}&subject_id={world.algo}')
    assert ok.status_code == 200 and b'82.0' in ok.data
    denied = world.teacher.client.get(f'/assessments/calculate?student_id={world.ann}&subject_id={world.db}')
    assert denied.status_code == 403
    assert world.teacher.client.get('/assessments/calculate').status_code == 200   # the picker form


def test_calculation_page_flags_missing_components(world):
    with world.app.app_context():
        record_mark(world.ann, world.algo, 'CAT1', 40)
    page = world.teacher.client.get(f'/assessments/calculate?student_id={world.ann}&subject_id={world.algo}')
    assert b'Incomplete' in page.data and b'Not entered' in page.data
