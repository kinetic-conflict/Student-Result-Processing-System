import pytest

from db import execute_query
from tests.factories import make_student, make_subject, record_all_marks
from tests.helpers import post

FULL = {'CAT1': 42, 'CAT2': 38, 'CAT3': 45, 'ASSIGN': 40, 'PROJECT': 85, 'ENDSEM': 78}


@pytest.fixture
def admin(sign_in):
    return sign_in('admin')


def config(app):
    with app.app_context():
        return {r['assessment_code']: (float(r['maximum_marks']), float(r['weight_percentage']))
                for r in execute_query('SELECT * FROM assessments')}


def form(app, **overrides):
    with app.app_context():
        current = execute_query('SELECT * FROM assessments ORDER BY assessment_id')
    data = {}
    for row in current:
        data[f"max_{row['assessment_id']}"] = str(row['maximum_marks'])
        data[f"weight_{row['assessment_id']}"] = str(row['weight_percentage'])
    for key, value in overrides.items():
        code, kind = key.rsplit('__', 1)
        assessment_id = next(r['assessment_id'] for r in current if r['assessment_code'] == code)
        data[f'{kind}_{assessment_id}'] = value
    return data


def test_the_page_shows_the_current_settings(app, admin):
    page = admin.client.get('/admin/assessment-config').data
    assert b'CAT1' in page and b'End Semester Examination' in page
    assert b'100' in page


def test_balanced_changes_are_saved_applied_and_audited(app, admin):
    with app.app_context():
        student, subject = make_student(), make_subject()
        record_all_marks(student, subject, FULL)
    response = post(admin.client, '/admin/assessment-config',
                    form(app, CAT1__weight='5', ENDSEM__weight='35'))
    assert response.status_code == 302
    assert config(app)['CAT1'][1] == 5 and config(app)['ENDSEM'][1] == 35
    with app.app_context():
        assert 'assessment_config.update' in [r['action'] for r in execute_query('SELECT action FROM audit_log')]
    # the very next result reflects the new weights (see test_result_queries for the arithmetic)
    assert b'81.4' in admin.client.get('/assessments/results').data


def test_weights_must_total_100_and_nothing_is_saved_otherwise(app, admin):
    before = config(app)
    response = post(admin.client, '/admin/assessment-config', form(app, CAT1__weight='20'))
    assert response.status_code == 200
    assert b'add up to 100' in response.data
    assert b'value="20"' in response.data          # what was typed stays on the form
    assert config(app) == before


@pytest.mark.parametrize('overrides, message', [
    ({'CAT1__max': 'abc'}, b'must be a number'),
    ({'CAT1__weight': ''}, b'is required'),
    ({'CAT1__max': '0'}, b'greater than 0'),
    ({'CAT1__weight': '-5'}, b'greater than 0'),
])
def test_bad_values_are_rejected(app, admin, overrides, message):
    before = config(app)
    response = post(admin.client, '/admin/assessment-config', form(app, **overrides))
    assert response.status_code == 200 and message in response.data
    assert config(app) == before


def test_a_maximum_cannot_drop_below_recorded_marks(app, admin):
    with app.app_context():
        record_all_marks(make_student(), make_subject(), FULL)
    response = post(admin.client, '/admin/assessment-config', form(app, CAT1__max='40'))
    assert response.status_code == 200 and b'cannot be lower' in response.data
    assert config(app)['CAT1'][0] == 50


def test_faculty_and_students_cannot_reach_the_settings(app, sign_in):
    for role in ('faculty', 'student'):
        who = sign_in(role)
        assert who.client.get('/admin/assessment-config').status_code == 403
        assert post(who.client, '/admin/assessment-config', form(app, CAT1__weight='5',
                                                                  ENDSEM__weight='35')).status_code == 403
    assert config(app)['CAT1'][1] == 15
