import pytest

from db import execute_query, execute_update
from services import access, auth_service
from tests.factories import assign, make_faculty, make_student, make_subject, make_user


@pytest.fixture
def world(ctx):
    """Two subjects in semester 3 and one in semester 5; students in semesters 3 and 5."""
    ids = {
        'algo': make_subject('CS301', 'Algorithms', 3),
        'db': make_subject('CS302', 'Databases', 3),
        'ml': make_subject('CS501', 'Machine Learning', 5),
        'ann': make_student('S001', 'Ann', 3),
        'ben': make_student('S002', 'Ben', 3),
        'cat': make_student('S003', 'Cat', 5),
        'fac': make_faculty('F001', 'Dr Rao'),
    }
    assign(ids['fac'], ids['algo'])
    ids['admin'] = auth_service.get_user(make_user('boss', 'admin'))
    ids['teacher'] = auth_service.get_user(make_user('rao', 'faculty', faculty_id=ids['fac']))
    ids['ann_user'] = auth_service.get_user(make_user('ann', 'student', student_id=ids['ann']))
    return ids


def test_admin_may_write_any_student_and_subject(world):
    assert access.can_write_marks(world['admin'], world['cat'], world['algo'])


def test_faculty_may_write_an_assigned_subject_for_students_in_its_semester(world):
    assert access.can_write_marks(world['teacher'], world['ann'], world['algo'])
    assert access.can_write_marks(world['teacher'], world['ben'], world['algo'])


def test_faculty_may_not_write_a_subject_they_are_not_assigned(world):
    assert not access.can_write_marks(world['teacher'], world['ann'], world['db'])


def test_faculty_may_not_write_for_a_student_outside_the_subjects_semester(world):
    assign(world['fac'], world['ml'])
    assert access.can_write_marks(world['teacher'], world['cat'], world['ml'])
    assert not access.can_write_marks(world['teacher'], world['ann'], world['ml'])
    assert not access.can_write_marks(world['teacher'], world['cat'], world['algo'])


def test_an_inactive_faculty_record_loses_access(world):
    execute_update('UPDATE faculty SET is_active = 0 WHERE faculty_id = %s', (world['fac'],))
    assert not access.can_write_marks(world['teacher'], world['ann'], world['algo'])


def test_students_can_never_write_marks(world):
    assert not access.can_write_marks(world['ann_user'], world['ann'], world['algo'])


def test_unknown_ids_are_simply_refused(world):
    assert not access.can_write_marks(world['admin'], 9999, world['algo'])
    assert not access.can_write_marks(world['teacher'], world['ann'], 9999)


def rows_seen(user):
    sql, params = access.scope_filter(user)
    return {row['full_name'] for row in execute_query(
        'SELECT s.full_name FROM students s JOIN subjects sub ON 1 = 1 WHERE 1 = 1' + sql, params)}


def test_scope_filter_pins_a_student_to_their_own_rows(world):
    assert rows_seen(world['ann_user']) == {'Ann'}


def test_scope_filter_limits_faculty_to_assigned_subjects_and_matching_semesters(world):
    assert rows_seen(world['teacher']) == {'Ann', 'Ben'}


def test_scope_filter_leaves_admins_unrestricted(world):
    assert rows_seen(world['admin']) == {'Ann', 'Ben', 'Cat'}


def test_a_faculty_account_without_assignments_sees_nothing(ctx):
    teacher = auth_service.get_user(make_user('idle', 'faculty', faculty_id=make_faculty('F009')))
    make_student('S001', 'Ann', 3)
    assert rows_seen(teacher) == set()


def test_students_for_subject_lists_the_semester_cohort_within_scope(world):
    names = lambda user, subject: [s['full_name'] for s in access.students_for_subject(user, subject)]
    assert names(world['admin'], world['algo']) == ['Ann', 'Ben']
    assert names(world['teacher'], world['algo']) == ['Ann', 'Ben']
    assert names(world['teacher'], world['db']) == []        # not assigned
    assert names(world['ann_user'], world['algo']) == ['Ann']


def test_assigned_subjects(world):
    codes = lambda user: [s['subject_code'] for s in access.subjects_for(user)]
    assert codes(world['teacher']) == ['CS301']
    assert codes(world['admin']) == ['CS301', 'CS302', 'CS501']
    assert codes(world['ann_user']) == []


def test_students_for_lists_each_visible_student_once(world):
    names = lambda user: [s['full_name'] for s in access.students_for(user)]
    assert names(world['admin']) == ['Ann', 'Ben', 'Cat']
    assert names(world['teacher']) == ['Ann', 'Ben']
    assert names(world['ann_user']) == ['Ann']


def test_can_manage_subject(world):
    assert access.can_manage_subject(world['admin'], world['db'])
    assert access.can_manage_subject(world['teacher'], world['algo'])
    assert not access.can_manage_subject(world['teacher'], world['db'])
    assert not access.can_manage_subject(world['ann_user'], world['algo'])
    execute_update('UPDATE faculty SET is_active = 0 WHERE faculty_id = %s', (world['fac'],))
    assert not access.can_manage_subject(world['teacher'], world['algo'])
