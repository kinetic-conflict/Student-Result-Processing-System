from types import SimpleNamespace

import pytest

from tests.factories import make_exam, make_legacy_mark, make_student, make_subject


@pytest.fixture
def world(app, sign_in):
    with app.app_context():
        w = SimpleNamespace(
            algo=make_subject('CS301', 'Algorithms', 3), db=make_subject('CS302', 'Databases', 3),
            ann=make_student('S001', 'Ann Rao', 3), ben=make_student('S002', 'Ben Das', 3),
            exam=make_exam('Mid Term'))
        make_legacy_mark(w.ann, w.algo, w.exam, 95)
        make_legacy_mark(w.ann, w.db, w.exam, 88)
        make_legacy_mark(w.ben, w.algo, w.exam, 30)
        make_legacy_mark(w.ben, w.db, w.exam, 75)
    w.admin = sign_in('admin')
    return w


def get(world, url):
    response = world.admin.client.get(url)
    assert response.status_code == 200, url
    assert b'Traceback' not in response.data
    return response.data


def test_report_index(world):
    assert b'Reports' in get(world, '/reports')


def test_student_report_groups_by_examination_and_totals_them(world):
    page = get(world, '/reports/student?registration_number=S001')
    assert b'Ann Rao' in page and b'Mid Term' in page
    assert b'183' in page                      # 95 + 88


def test_student_report_for_an_unknown_registration_number(world):
    assert b'not found' in get(world, '/reports/student?registration_number=NOPE').lower()


def test_examination_and_subject_reports(world):
    exam = get(world, f'/reports/examination?exam_id={world.exam}')
    assert b'Mid Term' in exam and b'S001' in exam
    subject = get(world, f'/reports/subject?subject_id={world.algo}')
    assert b'CS301' in subject


def test_top_failed_and_incomplete_reports(world):
    top = get(world, '/reports/top-performers')
    assert b'Ann Rao' in top and b'Ben Das' not in top
    failed = get(world, '/reports/failed-students')
    assert b'Ben Das' in failed and b'Ann Rao' not in failed
    assert b'S001' in get(world, '/reports/incomplete')


def test_reports_survive_junk_parameters(world):
    for url in ('/reports/examination?exam_id=abc', '/reports/subject?subject_id=%27',
                '/reports/student?registration_number=%25'):
        assert world.admin.client.get(url).status_code == 200, url


def test_reports_state_the_thresholds_they_use(world):
    assert b'85%' in get(world, '/reports/top-performers')
    assert b'5 subjects' in get(world, '/reports/incomplete')
