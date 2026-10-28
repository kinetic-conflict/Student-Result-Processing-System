from decimal import Decimal

import pytest

from db import execute_query
from services import audit, auth_service, marks_service
from services.marks_service import AccessDenied
from services.validation import ValidationError
from tests.factories import assign, make_faculty, make_student, make_subject, make_user, record_mark


@pytest.fixture
def world(ctx):
    ids = {
        'algo': make_subject('CS301', 'Algorithms', 3),
        'db': make_subject('CS302', 'Databases', 3),
        'ann': make_student('S001', 'Ann', 3),
        'ben': make_student('S002', 'Ben', 3),
        'cat': make_student('S003', 'Cat', 5),
        'fac': make_faculty('F001'),
    }
    assign(ids['fac'], ids['algo'])
    ids['admin'] = auth_service.get_user(make_user('boss', 'admin'))
    ids['teacher'] = auth_service.get_user(make_user('rao', 'faculty', faculty_id=ids['fac']))
    ids['ann_user'] = auth_service.get_user(make_user('ann', 'student', student_id=ids['ann']))
    return ids


def stored(student, subject):
    rows = execute_query(
        'SELECT a.assessment_code AS code, am.marks_obtained AS marks FROM assessment_marks am '
        'JOIN assessments a ON a.assessment_id = am.assessment_id '
        'WHERE am.student_id = %s AND am.subject_id = %s ORDER BY a.assessment_id', (student, subject))
    return {row['code']: row['marks'] for row in rows}


def D(value):
    return Decimal(str(value))


def test_admin_saves_marks_for_several_students_at_once(world):
    changed = marks_service.save_marks(world['admin'], world['algo'], {
        world['ann']: {'CAT1': D(42), 'ENDSEM': D('78.5')},
        world['ben']: {'CAT1': D(30)},
    })
    assert changed == 3
    assert stored(world['ann'], world['algo']) == {'CAT1': 42, 'ENDSEM': Decimal('78.5')}
    assert stored(world['ben'], world['algo']) == {'CAT1': 30}


def test_faculty_saves_for_their_subject_and_cohort(world):
    marks_service.save_marks(world['teacher'], world['algo'], {world['ann']: {'CAT1': D(40)}})
    assert stored(world['ann'], world['algo']) == {'CAT1': 40}


def test_faculty_cannot_save_for_a_subject_they_do_not_teach(world):
    with pytest.raises(AccessDenied):
        marks_service.save_marks(world['teacher'], world['db'], {world['ann']: {'CAT1': D(40)}})
    assert stored(world['ann'], world['db']) == {}


def test_faculty_cannot_save_for_a_student_outside_the_cohort(world):
    with pytest.raises(AccessDenied):
        marks_service.save_marks(world['teacher'], world['algo'], {world['cat']: {'CAT1': D(40)}})


def test_one_forbidden_student_blocks_the_whole_save(world):
    with pytest.raises(AccessDenied):
        marks_service.save_marks(world['teacher'], world['algo'], {
            world['ann']: {'CAT1': D(40)}, world['cat']: {'CAT1': D(40)}})
    assert stored(world['ann'], world['algo']) == {}


def test_students_cannot_save_marks_at_all(world):
    with pytest.raises(AccessDenied):
        marks_service.save_marks(world['ann_user'], world['algo'], {world['ann']: {'ENDSEM': D(100)}})


@pytest.mark.parametrize('code, value, fragment', [
    ('CAT1', D(-1), 'CAT1'),
    ('CAT1', D(51), '50'),
    ('PROJECT', D('100.01'), '100'),
    ('CAT1', D('40.123'), 'decimal places'),
    ('NOPE', D(10), 'NOPE'),
])
def test_invalid_marks_are_rejected(world, code, value, fragment):
    with pytest.raises(ValidationError, match=fragment):
        marks_service.save_marks(world['admin'], world['algo'], {world['ann']: {code: value}})
    assert stored(world['ann'], world['algo']) == {}


def test_a_bad_mark_anywhere_means_nothing_is_saved(world):
    with pytest.raises(ValidationError):
        marks_service.save_marks(world['admin'], world['algo'], {
            world['ann']: {'CAT1': D(40)}, world['ben']: {'CAT1': D(99)}})
    assert stored(world['ann'], world['algo']) == {}


def test_blank_values_leave_existing_marks_alone(world):
    record_mark(world['ann'], world['algo'], 'CAT1', 40)
    marks_service.save_marks(world['admin'], world['algo'], {
        world['ann']: {'CAT1': None, 'CAT2': D(35)}})
    assert stored(world['ann'], world['algo']) == {'CAT1': 40, 'CAT2': 35}


def test_saving_nothing_is_an_error(world):
    with pytest.raises(ValidationError, match='No marks'):
        marks_service.save_marks(world['admin'], world['algo'], {world['ann']: {'CAT1': None}})


def test_updates_overwrite_and_are_audited_with_old_and_new_values(world):
    record_mark(world['ann'], world['algo'], 'CAT1', 40)
    marks_service.save_marks(world['teacher'], world['algo'], {world['ann']: {'CAT1': D(45)}},
                             ip='10.1.1.1')
    assert stored(world['ann'], world['algo']) == {'CAT1': 45}
    (entry,) = audit.recent(10)
    assert entry['username'] == 'rao' and entry['action'] == 'mark.save'
    assert 'S001' in entry['detail'] and 'CAT1' in entry['detail']
    assert '40' in entry['detail'] and '45' in entry['detail']
    assert entry['ip_address'] == '10.1.1.1'


def test_resaving_identical_values_changes_and_logs_nothing(world):
    record_mark(world['ann'], world['algo'], 'CAT1', 40)
    assert marks_service.save_marks(world['admin'], world['algo'], {world['ann']: {'CAT1': D(40)}}) == 0
    assert audit.count() == 0


# ---- editing and deleting one mark ------------------------------------------

def mark_id(student, subject, code):
    return execute_query(
        'SELECT am.assessment_mark_id AS id FROM assessment_marks am '
        'JOIN assessments a ON a.assessment_id = am.assessment_id '
        'WHERE am.student_id = %s AND am.subject_id = %s AND a.assessment_code = %s',
        (student, subject, code))[0]['id']


def test_change_mark_respects_scope_and_range(world):
    record_mark(world['ann'], world['algo'], 'CAT1', 40)
    record_mark(world['ann'], world['db'], 'CAT1', 40)
    in_scope = mark_id(world['ann'], world['algo'], 'CAT1')
    out_of_scope = mark_id(world['ann'], world['db'], 'CAT1')

    marks_service.change_mark(world['teacher'], in_scope, D(44))
    assert stored(world['ann'], world['algo']) == {'CAT1': 44}
    with pytest.raises(ValidationError, match='50'):
        marks_service.change_mark(world['teacher'], in_scope, D(51))
    with pytest.raises(AccessDenied):
        marks_service.change_mark(world['teacher'], out_of_scope, D(44))
    with pytest.raises(AccessDenied):
        marks_service.change_mark(world['teacher'], 99999, D(44))   # no existence oracle for non-admins
    assert stored(world['ann'], world['db']) == {'CAT1': 40}


def test_admin_gets_not_found_for_a_missing_mark(world):
    with pytest.raises(LookupError):
        marks_service.change_mark(world['admin'], 99999, D(10))


def test_only_admins_delete_marks(world):
    record_mark(world['ann'], world['algo'], 'CAT1', 40)
    target = mark_id(world['ann'], world['algo'], 'CAT1')
    with pytest.raises(AccessDenied):
        marks_service.delete_mark(world['teacher'], target)
    assert stored(world['ann'], world['algo']) == {'CAT1': 40}
    marks_service.delete_mark(world['admin'], target)
    assert stored(world['ann'], world['algo']) == {}
    assert audit.recent(1)[0]['action'] == 'mark.delete'
