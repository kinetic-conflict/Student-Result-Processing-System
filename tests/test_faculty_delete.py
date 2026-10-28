"""Deleting a faculty member removes the profile, the login and the assignments, and nothing else."""
from types import SimpleNamespace

import mysql.connector
import pytest

from db import execute_query
from services import auth_service, exam_results, faculty_service, result_queries
from tests.factories import (assign, make_exam, make_faculty, make_legacy_mark, make_student,
                             make_subject, record_all_marks, record_mark)
from tests.helpers import post

FULL = {'CAT1': 42, 'CAT2': 38, 'CAT3': 45, 'ASSIGN': 40, 'PROJECT': 85, 'ENDSEM': 78}
STUDENT_TABLES = ('students', 'subjects', 'examinations', 'marks', 'assessments', 'assessment_marks')


def rows(app, sql, params=()):
    with app.app_context():
        return execute_query(sql, params)


@pytest.fixture
def world(app, sign_in):
    with app.app_context():
        w = SimpleNamespace(
            algo=make_subject('CS301', 'Algorithms', 3),
            db=make_subject('CS302', 'Databases', 3),
            ann=make_student('S001', 'Ann Rao', 3),
            ben=make_student('S002', 'Ben Das', 3),
            exam=make_exam(),
            leaving=make_faculty('F100', 'Dr Leaving', 'leaving@example.test'),
            staying=make_faculty('F200', 'Dr Staying'),
        )
        assign(w.leaving, w.algo)
        assign(w.leaving, w.db)
        assign(w.staying, w.algo)
        make_legacy_mark(w.ann, w.algo, w.exam, 71, 100)
        make_legacy_mark(w.ben, w.algo, w.exam, 38, 100)
        record_all_marks(w.ann, w.algo, FULL)
        record_mark(w.ben, w.algo, 'CAT1', 0)               # a zero, and an otherwise incomplete record
    w.app = app
    w.admin = sign_in('admin')
    w.leaver = sign_in('faculty', faculty_id=w.leaving)
    w.stayer = sign_in('faculty', faculty_id=w.staying)
    # The faculty member enters a mark through the app, so the audit log holds work done by their login.
    assert post(w.leaver.client, f'/assessments/subjects/{w.algo}',
                {f'm_{w.ann}_CAT1': '41'}).status_code == 302
    return w


def student_data(world):
    """Every table that holds student results, row for row, plus the results calculated from them."""
    with world.app.app_context():
        admin = auth_service.get_user(world.admin.user_id)
        return {
            'tables': {table: execute_query(f'SELECT * FROM {table} ORDER BY 1') for table in STUDENT_TABLES},
            'weighted': result_queries.weighted_results(admin, per_page=100)['rows'],
            'exams': {s: exam_results.student_exam_results(s) for s in (world.ann, world.ben)},
        }


def delete(world, faculty_id, **kwargs):
    return post(world.admin.client, f'/admin/faculty/{faculty_id}/delete', **kwargs)


# ---- what is removed --------------------------------------------------------

def test_deleting_removes_the_profile_the_login_and_the_assignments(world):
    assert delete(world, world.leaving).status_code == 302
    assert rows(world.app, 'SELECT 1 FROM faculty WHERE faculty_id = %s', (world.leaving,)) == []
    assert rows(world.app, 'SELECT 1 FROM users WHERE faculty_id = %s', (world.leaving,)) == []
    assert rows(world.app, 'SELECT 1 FROM faculty_assignments WHERE faculty_id = %s', (world.leaving,)) == []


def test_marks_and_assessment_marks_stay_exactly_as_they_were(world):
    before = student_data(world)
    assert before['tables']['marks'] and before['tables']['assessment_marks']
    assert delete(world, world.leaving).status_code == 302
    assert rows(world.app, 'SELECT 1 FROM faculty WHERE faculty_id = %s', (world.leaving,)) == []
    after = student_data(world)
    assert after['tables']['marks'] == before['tables']['marks']
    assert after['tables']['assessment_marks'] == before['tables']['assessment_marks']


def test_every_student_result_is_unchanged(world):
    before = student_data(world)
    assert delete(world, world.leaving).status_code == 302
    assert rows(world.app, 'SELECT 1 FROM faculty WHERE faculty_id = %s', (world.leaving,)) == []
    assert student_data(world) == before


def test_other_faculty_accounts_subjects_and_students_are_not_touched(world):
    delete(world, world.leaving)
    assert [r['employee_id'] for r in rows(world.app, 'SELECT employee_id FROM faculty')] == ['F200']
    assert {r['user_id'] for r in rows(world.app, 'SELECT user_id FROM users')} == {
        world.admin.user_id, world.stayer.user_id}
    assert [r['subject_id'] for r in rows(world.app, 'SELECT subject_id FROM faculty_assignments')] == [world.algo]
    assert len(rows(world.app, 'SELECT 1 FROM subjects')) == 2
    assert len(rows(world.app, 'SELECT 1 FROM students')) == 2
    assert len(rows(world.app, 'SELECT 1 FROM examinations')) == 1


def test_the_deleted_members_login_stops_working_at_once(world):
    assert world.leaver.client.get('/faculty').status_code == 200
    delete(world, world.leaving)
    assert world.leaver.client.get('/faculty').status_code == 302


def test_a_member_without_a_login_can_be_deleted(world):
    with world.app.app_context():
        loner = make_faculty('F300', 'Dr Loner')
    assert delete(world, loner).status_code == 302
    assert rows(world.app, 'SELECT 1 FROM faculty WHERE faculty_id = %s', (loner,)) == []
    detail = rows(world.app, "SELECT detail FROM audit_log WHERE action = 'faculty.delete'")[0]['detail']
    assert 'no login' in detail


# ---- the audit trail --------------------------------------------------------

def test_the_deletion_is_recorded_without_secrets(world):
    delete(world, world.leaving)
    (entry,) = rows(world.app, "SELECT * FROM audit_log WHERE action = 'faculty.delete'")
    assert entry['entity'] == 'faculty' and entry['entity_id'] == str(world.leaving)
    assert entry['user_id'] == world.admin.user_id and entry['username'] == world.admin.username
    assert 'F100' in entry['detail'] and 'Dr Leaving' in entry['detail']
    assert world.leaver.username in entry['detail'] and '2 subject assignment' in entry['detail']
    assert 'password' not in entry['detail'].lower() and '$' not in entry['detail']


def test_earlier_audit_entries_of_the_deleted_login_survive(world):
    entries = rows(world.app, 'SELECT * FROM audit_log WHERE username = %s', (world.leaver.username,))
    assert entries, 'the faculty login should already have audited work'
    delete(world, world.leaving)
    after = rows(world.app, 'SELECT * FROM audit_log WHERE username = %s', (world.leaver.username,))
    assert [e['audit_id'] for e in after] == [e['audit_id'] for e in entries]
    assert all(e['user_id'] is None for e in after)      # the login is gone, the name stays


# ---- refusals ---------------------------------------------------------------

def test_an_unknown_faculty_member_is_not_found_and_nothing_changes(world):
    before = student_data(world)
    assert delete(world, 99999).status_code == 404
    assert len(rows(world.app, 'SELECT 1 FROM faculty')) == 2
    assert rows(world.app, "SELECT 1 FROM audit_log WHERE action = 'faculty.delete'") == []
    assert student_data(world) == before


def test_deleting_needs_a_post_with_a_csrf_token(world):
    assert world.admin.client.get(f'/admin/faculty/{world.leaving}/delete').status_code == 405
    assert post(world.admin.client, f'/admin/faculty/{world.leaving}/delete',
                {'csrf_token': None}).status_code == 400
    assert len(rows(world.app, 'SELECT 1 FROM faculty')) == 2


def test_only_administrators_can_delete(world):
    anonymous = world.app.test_client()
    assert post(anonymous, f'/admin/faculty/{world.staying}/delete').status_code == 302
    assert delete_as(world.stayer, world.staying).status_code == 403
    assert delete_as(world.leaver, world.staying).status_code == 403
    assert len(rows(world.app, 'SELECT 1 FROM faculty')) == 2


def delete_as(person, faculty_id):
    return post(person.client, f'/admin/faculty/{faculty_id}/delete')


def test_a_failure_part_way_rolls_everything_back(world, monkeypatch):
    def refuse(*args, **kwargs):
        raise mysql.connector.Error('simulated failure while writing the audit entry')

    monkeypatch.setattr('services.audit.record', refuse)
    before = student_data(world)
    response = delete(world, world.leaving, follow_redirects=True)
    assert response.status_code == 200 and b'could not be deleted' in response.data
    assert rows(world.app, 'SELECT 1 FROM faculty WHERE faculty_id = %s', (world.leaving,))
    assert rows(world.app, 'SELECT 1 FROM users WHERE faculty_id = %s', (world.leaving,))
    assert len(rows(world.app, 'SELECT 1 FROM faculty_assignments WHERE faculty_id = %s', (world.leaving,))) == 2
    assert student_data(world) == before


# ---- the page and the service -----------------------------------------------

def test_the_list_offers_delete_with_a_plain_warning(world):
    page = world.admin.client.get('/admin/faculty').data.decode()
    assert f'/admin/faculty/{world.leaving}/delete' in page
    assert 'Delete' in page and 'cannot be undone' in page
    assert 'marks and results are not affected' in page.lower()


def test_the_service_reports_what_it_removed(ctx):
    faculty = make_faculty('F500', 'Dr Five')
    assign(faculty, make_subject('CS501'))
    result = faculty_service.delete_faculty(faculty, None)
    assert result == {'employee_id': 'F500', 'full_name': 'Dr Five', 'username': None, 'assignments': 1}
    with pytest.raises(LookupError):
        faculty_service.delete_faculty(faculty, None)
