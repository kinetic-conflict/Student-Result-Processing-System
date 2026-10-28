from types import SimpleNamespace

import pytest

from db import execute_query
from tests.factories import (assign, make_exam, make_faculty, make_legacy_mark, make_student,
                             make_subject)
from tests.helpers import post


@pytest.fixture
def world(app, sign_in):
    with app.app_context():
        w = SimpleNamespace(
            algo=make_subject('CS301', 'Algorithms', 3), db=make_subject('CS302', 'Databases', 3),
            ann=make_student('S001', 'Ann Rao', 3), ben=make_student('S002', 'Ben Das', 3),
            cat=make_student('S003', 'Cat Roy', 5), exam=make_exam())
        fac = make_faculty('F100')
        assign(fac, w.algo)
    w.app = app
    w.admin = sign_in('admin')
    w.teacher = sign_in('faculty', faculty_id=fac)
    return w


def mark_rows(world):
    with world.app.app_context():
        return execute_query('SELECT * FROM marks ORDER BY mark_id')


def form(world, **overrides):
    data = {'student_id': str(world.ann), 'subject_id': str(world.algo), 'exam_id': str(world.exam),
            'marks_obtained': '75', 'maximum_marks': '100'}
    data.update(overrides)
    return data


def test_adding_a_legacy_mark(world):
    assert post(world.admin.client, '/marks/add', form(world)).status_code == 302
    (row,) = mark_rows(world)
    assert float(row['marks_obtained']) == 75 and float(row['maximum_marks']) == 100


@pytest.mark.parametrize('overrides, message', [
    ({'marks_obtained': '101'}, b'cannot exceed'),
    ({'marks_obtained': '-1'}, b'at least 0'),
    ({'marks_obtained': 'nan'}, b'must be a number'),
    ({'marks_obtained': ''}, b'is required'),
    ({'maximum_marks': '0'}, b'greater than'),
    ({'maximum_marks': 'inf'}, b'must be a number'),
    ({'student_id': 'abc'}, b'whole number'),
    ({'student_id': '99999'}, b'existing'),
])
def test_legacy_mark_validation(world, overrides, message):
    response = post(world.admin.client, '/marks/add', form(world, **overrides))
    assert response.status_code == 200 and message in response.data
    assert mark_rows(world) == []


def test_duplicate_legacy_marks_are_explained(world):
    post(world.admin.client, '/marks/add', form(world))
    response = post(world.admin.client, '/marks/add', form(world, marks_obtained='80'))
    assert response.status_code == 200 and b'already exist' in response.data
    assert len(mark_rows(world)) == 1


def test_editing_and_deleting_a_legacy_mark(world):
    with world.app.app_context():
        mark = make_legacy_mark(world.ann, world.algo, world.exam, 60)
    assert world.admin.client.get(f'/marks/{mark}/edit').status_code == 200
    assert post(world.admin.client, f'/marks/{mark}/edit',
                {'marks_obtained': '65', 'maximum_marks': '100'}).status_code == 302
    assert float(mark_rows(world)[0]['marks_obtained']) == 65
    too_high = post(world.admin.client, f'/marks/{mark}/edit',
                    {'marks_obtained': '200', 'maximum_marks': '100'})
    assert too_high.status_code == 200 and b'cannot exceed' in too_high.data
    assert post(world.admin.client, f'/marks/{mark}/delete').status_code == 302
    assert mark_rows(world) == []


def test_unknown_mark_redirects_with_a_message(world):
    assert b'not found' in world.admin.client.get('/marks/99999/edit', follow_redirects=True).data


def test_legacy_mark_list_filters_and_survives_junk(world):
    with world.app.app_context():
        make_legacy_mark(world.ann, world.algo, world.exam, 90)
        make_legacy_mark(world.ben, world.algo, world.exam, 50)
    page = world.admin.client.get(f'/marks?student_id={world.ann}').data
    table = page[page.index(b'<table'):]       # the filter dropdown lists everyone
    assert b'S001' in table and b'S002' not in table
    for query in ('?student_id=x', '?subject_id=%27', '?exam_id=-1', '?page=zzz'):
        assert world.admin.client.get('/marks' + query).status_code == 200, query


# ---- result search ----------------------------------------------------------

@pytest.fixture
def searchable(world):
    with world.app.app_context():
        make_legacy_mark(world.ann, world.algo, world.exam, 90)
        make_legacy_mark(world.ann, world.db, world.exam, 40)
        make_legacy_mark(world.cat, world.algo, world.exam, 55)
    return world


def test_admin_searches_by_registration_or_name(searchable):
    by_reg = searchable.admin.client.get('/results?search=S001&filter_type=registration').data
    assert b'Ann Rao' in by_reg and b'Cat Roy' not in by_reg
    by_name = searchable.admin.client.get('/results?search=roy&filter_type=name').data
    assert b'Cat Roy' in by_name and b'Ann Rao' not in by_name


def test_an_unknown_filter_type_does_not_turn_into_list_everything(searchable):
    page = searchable.admin.client.get('/results?search=S001&filter_type=bogus').data
    assert b'Ann Rao' in page and b'Cat Roy' not in page


def test_wildcards_in_the_search_are_literal(searchable):
    page = searchable.admin.client.get('/results?search=%25').data
    assert b'Ann Rao' not in page


def test_a_search_is_required_before_any_results_are_listed(searchable):
    page = searchable.admin.client.get('/results').data
    assert b'Ann Rao' not in page


def test_faculty_results_are_limited_to_assigned_subjects_and_cohort(searchable):
    page = searchable.teacher.client.get('/results?search=S0&filter_type=registration').data
    assert b'Ann Rao' in page          # CS301, semester 3
    assert b'CS302' not in page        # not theirs
    assert b'Cat Roy' not in page      # semester 5, outside the cohort
