from decimal import Decimal

import pytest

from db import like_contains
from services import assessment_config, auth_service, marks_service, result_queries
from tests.factories import (assign, make_faculty, make_student, make_subject, make_user,
                             record_all_marks, record_mark)

FULL = {'CAT1': 42, 'CAT2': 38, 'CAT3': 45, 'ASSIGN': 40, 'PROJECT': 85, 'ENDSEM': 78}   # totals 82.0


@pytest.fixture
def world(ctx):
    ids = {
        'algo': make_subject('CS301', 'Algorithms', 3),
        'db': make_subject('CS302', 'Databases', 3),
        'ann': make_student('S001', 'Ann Rao', 3),
        'ben': make_student('S002', 'Ben Das', 3),
        'cat': make_student('S003', 'Cat Roy', 5),
        'fac': make_faculty('F001'),
    }
    assign(ids['fac'], ids['algo'])
    record_all_marks(ids['ann'], ids['algo'], FULL)
    record_mark(ids['ann'], ids['db'], 'CAT1', 30)                    # incomplete
    record_all_marks(ids['ben'], ids['algo'], dict(FULL, ENDSEM=100))
    record_mark(ids['cat'], ids['algo'], 'CAT1', 10)                  # wrong semester for CS301
    ids['admin'] = auth_service.get_user(make_user('boss', 'admin'))
    ids['teacher'] = auth_service.get_user(make_user('rao', 'faculty', faculty_id=ids['fac']))
    ids['ann_user'] = auth_service.get_user(make_user('ann', 'student', student_id=ids['ann']))
    return ids


def listing(user, **filters):
    return result_queries.weighted_results(user, **filters)


def keyed(rows):
    return {(r['registration_number'], r['subject_code']): r for r in rows}


def test_a_complete_record_is_graded_with_the_configured_weights(world):
    row = keyed(listing(world['admin'])['rows'])[('S001', 'CS301')]
    assert row['marks']['CAT1'] == 42
    assert row['result']['total_weighted_score'] == 82.0
    assert (row['result']['grade'], row['result']['status']) == ('A', 'Pass')


def test_a_partial_record_is_incomplete_not_zero(world):
    row = keyed(listing(world['admin'])['rows'])[('S001', 'CS302')]
    assert row['result']['status'] == 'Incomplete'
    assert row['result']['total_weighted_score'] is None


def test_admin_sees_everything_ordered_by_registration_then_subject(world):
    rows = listing(world['admin'])['rows']
    assert [(r['registration_number'], r['subject_code']) for r in rows] == [
        ('S001', 'CS301'), ('S001', 'CS302'), ('S002', 'CS301'), ('S003', 'CS301')]


def test_a_student_sees_only_their_own_records(world):
    rows = listing(world['ann_user'])['rows']
    assert {r['registration_number'] for r in rows} == {'S001'}
    assert len(rows) == 2


def test_a_student_cannot_widen_their_view_with_filters(world):
    rows = listing(world['ann_user'], student_id=world['ben'])['rows']
    assert rows == []
    assert listing(world['ann_user'], search='Ben')['rows'] == []


def test_faculty_see_only_assigned_subjects_for_their_cohort(world):
    rows = listing(world['teacher'])['rows']
    assert [(r['registration_number'], r['subject_code']) for r in rows] == [
        ('S001', 'CS301'), ('S002', 'CS301')]


def test_filters_narrow_the_listing(world):
    assert len(listing(world['admin'], subject_id=world['db'])['rows']) == 1
    assert len(listing(world['admin'], student_id=world['ben'])['rows']) == 1
    assert [r['registration_number'] for r in listing(world['admin'], search='roy')['rows']] == ['S003']
    assert [r['registration_number'] for r in listing(world['admin'], search='S002')['rows']] == ['S002']


def test_search_treats_wildcards_literally(world):
    assert listing(world['admin'], search='%')['rows'] == []
    assert listing(world['admin'], search='_')['rows'] == []


def test_paging(world):
    first = listing(world['admin'], per_page=3)
    assert first['page'].pages == 2 and len(first['rows']) == 3
    second = listing(world['admin'], per_page=3, raw_page='2')
    assert len(second['rows']) == 1 and second['page'].page == 2


def test_changing_a_mark_changes_the_result_immediately(world):
    assert keyed(listing(world['admin'])['rows'])[('S001', 'CS301')]['result']['grade'] == 'A'
    marks_service.save_marks(world['admin'], world['algo'], {world['ann']: {'ENDSEM': Decimal(100)}})
    result = keyed(listing(world['admin'])['rows'])[('S001', 'CS301')]['result']
    assert result['total_weighted_score'] == 87.5     # 82 + (100 - 78) * 25%


def test_changing_the_weights_changes_the_result_immediately(world):
    config = assessment_config.load_config()
    values = {a['assessment_id']: (a['max'], a['weight']) for a in config}
    by_code = {a['code']: a['assessment_id'] for a in config}
    values[by_code['CAT1']] = (Decimal(50), Decimal(5))
    values[by_code['ENDSEM']] = (Decimal(100), Decimal(35))
    assessment_config.update_config(values)
    result = keyed(listing(world['admin'])['rows'])[('S001', 'CS301')]['result']
    # CAT1 42/50 at 5% = 4.2 (was 12.6); ENDSEM 78/100 at 35% = 27.3 (was 19.5)
    assert result['total_weighted_score'] == 81.4


def test_like_contains_escapes_wildcards():
    assert like_contains('50%_off\\') == '%50\\%\\_off\\\\%'
