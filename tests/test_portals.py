from types import SimpleNamespace

import pytest

from db import execute_update
from tests.factories import (assign, make_faculty, make_student, make_subject, record_all_marks,
                             record_mark)
from tests.helpers import login

FULL = {'CAT1': 42, 'CAT2': 38, 'CAT3': 45, 'ASSIGN': 40, 'PROJECT': 85, 'ENDSEM': 78}


@pytest.fixture
def world(app, sign_in):
    with app.app_context():
        w = SimpleNamespace(
            algo=make_subject('CS301', 'Algorithms', 3),
            db=make_subject('CS302', 'Databases', 3),
            ann=make_student('S001', 'Ann Rao', 3),
            ben=make_student('S002', 'Ben Das', 3),
        )
        fac = make_faculty('F100', 'Dr First')
        assign(fac, w.algo)
        record_all_marks(w.ann, w.algo, FULL)
        record_mark(w.ann, w.db, 'CAT1', 30)
        record_all_marks(w.ben, w.algo, dict(FULL, ENDSEM=100))
        execute_update(
            "INSERT INTO examinations (exam_name, academic_year, semester) VALUES ('Mid Term', '2024-2025', 3)")
        for student, marks in ((w.ann, 71), (w.ben, 33)):
            execute_update(
                'INSERT INTO marks (student_id, subject_id, exam_id, marks_obtained, maximum_marks) '
                'VALUES (%s, %s, 1, %s, 100)', (student, w.algo, marks))
    w.app = app
    w.admin = sign_in('admin')
    w.teacher = sign_in('faculty', faculty_id=fac)
    w.ann_user = sign_in('student', student_id=w.ann)
    w.ben_user = sign_in('student', student_id=w.ben)
    return w


@pytest.mark.parametrize('role, landing', [('admin', '/admin'), ('faculty', '/faculty'), ('student', '/me')])
def test_each_role_lands_on_its_own_home_page(app, sign_in, role, landing):
    who = sign_in(role)
    assert who.client.get('/').headers['Location'].endswith(landing)
    assert who.client.get(landing).status_code == 200


# ---- the student portal -----------------------------------------------------

def test_a_student_sees_their_own_results(world):
    page = world.ann_user.client.get('/me').data
    assert b'Ann Rao' in page and b'S001' in page
    assert b'82.0' in page                      # weighted total for CS301
    assert b'Incomplete' in page                # CS302 has one component only
    assert b'Mid Term' in page and b'71' in page


def test_a_student_never_sees_another_students_data(world):
    for url in ('/me', '/me/marksheet'):
        page = world.ann_user.client.get(url).data
        assert b'Ben Das' not in page and b'S002' not in page, url
        assert b'87.5' not in page and b'33' not in page.replace(b'33px', b''), url


def test_client_supplied_ids_cannot_redirect_the_student_view(world):
    page = world.ann_user.client.get(f'/me?student_id={world.ben}&registration_number=S002').data
    assert b'Ann Rao' in page and b'Ben Das' not in page
    sheet = world.ann_user.client.get(f'/me/marksheet?student_id={world.ben}').data
    assert b'Ann Rao' in sheet and b'Ben Das' not in sheet


def test_marksheet_is_printable(world):
    page = world.ann_user.client.get('/me/marksheet').data
    assert b'data-print' in page and b'Statement of marks' in page


def test_students_are_refused_every_staff_page_that_could_expose_other_students(world):
    client = world.ann_user.client
    for url in (f'/students/{world.ben}', '/students', '/results?search=S002',
                '/reports/student?registration_number=S002', f'/marks?student_id={world.ben}',
                f'/assessments/calculate?student_id={world.ben}&subject_id={world.algo}',
                f'/assessments?student_id={world.ben}', '/assessments/results',
                f'/assessments/subjects/{world.algo}', '/faculty', '/admin',
                f'/examinations/1/results'):
        assert client.get(url).status_code == 403, url


def test_students_cannot_post_changes_either(world):
    from tests.helpers import post
    for url, data in ((f'/students/{world.ben}/delete', {}),
                      ('/assessments/enter', {'student_id': str(world.ben), 'subject_id': str(world.algo),
                                              'marks_CAT1': '50'}),
                      (f'/assessments/subjects/{world.algo}', {f'm_{world.ben}_CAT1': '50'})):
        assert post(world.ann_user.client, url, data).status_code == 403, url


def test_a_deactivated_student_loses_access_at_once(world, ctx):
    execute_update('UPDATE users SET is_active = 0 WHERE user_id = %s', (world.ann_user.user_id,))
    # the cookie is still signed, but the account no longer qualifies
    from services import auth_service
    auth_service.set_active(world.ann_user.user_id, False)
    assert world.ann_user.client.get('/me').status_code == 302


# ---- the faculty portal -----------------------------------------------------

def test_faculty_dashboard_lists_only_assigned_subjects_with_progress(world):
    page = world.teacher.client.get('/faculty').data
    assert b'CS301' in page and b'CS302' not in page
    assert b'Students in cohort' in page
    assert f'/assessments/subjects/{world.algo}'.encode() in page


def test_faculty_results_show_their_cohort_and_nothing_else(world):
    page = world.teacher.client.get('/assessments/results').data
    assert b'S001' in page and b'S002' in page
    assert b'CS302' not in page


def test_faculty_cannot_open_admin_record_pages(world):
    client = world.teacher.client
    for url in ('/students', f'/students/{world.ann}', '/subjects', '/examinations', '/marks',
                '/reports', '/reports/student?registration_number=S001', '/admin'):
        assert client.get(url).status_code == 403, url


def test_an_unassigned_faculty_account_sees_an_empty_dashboard(app, sign_in):
    idle = sign_in('faculty')
    page = idle.client.get('/faculty').data
    assert b'No subjects are assigned' in page


def test_pages_are_never_cached(world):
    assert 'no-store' in world.ann_user.client.get('/me').headers['Cache-Control']
