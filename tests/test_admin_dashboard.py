import re

from tests.factories import assign, make_faculty, make_student, make_subject, make_user


def number_after(page, label):
    match = re.search(rb'data-stat="' + label + rb'">(\d+)<', page)
    assert match, label
    return int(match.group(1))


def test_dashboard_counts_everything_the_admin_manages(app, sign_in):
    admin = sign_in('admin')
    with app.app_context():
        make_student('S1', 'One'), make_student('S2', 'Two')
        make_subject('A1'), make_subject('B1'), make_subject('C1')
        make_faculty('F1')
    page = admin.client.get('/admin').data
    assert number_after(page, b'students') == 2
    assert number_after(page, b'subjects') == 3
    assert number_after(page, b'faculty') == 1
    assert number_after(page, b'accounts') == 1


def test_dashboard_flags_work_that_needs_attention(app, sign_in):
    admin = sign_in('admin')
    with app.app_context():
        make_student('S1', 'Has No Login')
        taught, untaught = make_subject('TAUGHT'), make_subject('UNTAUGHT')
        busy, idle = make_faculty('F1', 'Busy'), make_faculty('F2', 'Idle Faculty')
        assign(busy, taught)
    page = admin.client.get('/admin').data
    assert b'Has No Login' not in page            # counts only, no personal data on the dashboard
    assert number_after(page, b'students-without-login') == 1
    assert number_after(page, b'subjects-without-faculty') == 1
    assert number_after(page, b'faculty-without-subjects') == 1


def test_a_database_outage_shows_the_outage_page_not_zeros(server, clean_db):
    from app import create_app
    from tests.conftest import app_settings
    from tests.helpers import login
    from tests.factories import make_user as _make_user
    settings = app_settings(server, clean_db)
    live = create_app(settings, testing=True)
    with live.app_context():
        _make_user('boss', 'admin')
    browser = live.test_client()
    login(browser, 'boss')
    live.config['DB_PORT'] = 1                    # the database "goes away" mid-session
    live.config['PROPAGATE_EXCEPTIONS'] = False
    page = browser.get('/admin')
    assert page.status_code == 503
    assert b'Could not connect to the MySQL database' in page.data
