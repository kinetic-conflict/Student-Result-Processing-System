"""Regression tests for findings from the independent security review."""
import logging
import threading
from decimal import Decimal

import mysql.connector
import pytest

from db import execute_query, execute_update
from services import assessment_config, audit, auth_service, marks_service
from services.validation import ValidationError
from tests.factories import (PASSWORD, assign, make_faculty, make_student, make_subject, make_user,
                             record_mark)
from tests.helpers import csrf, login, post


@pytest.fixture
def asha(ctx):
    make_user('asha', 'admin')
    return 'asha'


# ---- login throttle cannot be dodged with accented spellings ----------------

def test_accented_spellings_share_one_lockout_counter(app, asha):
    client = app.test_client()
    for spelling in ('asha', 'ásha', 'àsha', 'âsha', 'äsha', 'åsha'):
        login(client, spelling, 'wrong-password-1')
    assert login(client, 'asha').status_code == 429


# ---- inputs that used to cause a 500 ----------------------------------------

def test_a_non_ascii_csrf_token_is_just_rejected(app, asha):
    client = app.test_client()
    csrf(client)
    assert post(client, '/login', {'username': 'asha', 'password': PASSWORD, 'csrf_token': 'é'}).status_code == 400


def test_unicode_digits_in_an_id_do_not_crash_the_entry_form(app, sign_in):
    admin = sign_in('admin')
    assert admin.client.get('/assessments/enter?student_id=%C2%B2&subject_id=1').status_code == 200


def test_a_query_parameter_named_endpoint_does_not_break_paging(app, sign_in):
    admin = sign_in('admin')
    with app.app_context():
        for index in range(30):
            make_student(f'P{index:03}', f'Pager {index}')
    page = admin.client.get('/students?endpoint=x&page=1')
    assert page.status_code == 200 and b'Page 1 of 2' in page.data


@pytest.mark.parametrize('hostile', ['/%0d%0a', '/%09/evil.example', '/%0a', '/ /x', '/\t/evil.example'])
def test_control_characters_in_next_are_ignored(app, asha, hostile):
    client = app.test_client()
    response = post(client, f'/login?next={hostile}', {'username': 'asha', 'password': PASSWORD})
    assert response.status_code == 302
    assert response.headers['Location'].endswith('/admin')


# ---- mark saving under concurrent change ------------------------------------

@pytest.fixture
def marks_world(ctx):
    w = {'algo': make_subject('CS301', 'Algorithms', 3), 'ann': make_student('S001', 'Ann', 3)}
    w['admin'] = auth_service.get_user(make_user('boss', 'admin'))
    return w


def test_the_maximum_is_re_read_under_lock_so_a_stale_copy_cannot_let_a_bad_mark_in(marks_world, monkeypatch):
    stale = assessment_config.load_config()                       # CAT1 max 50
    execute_update("UPDATE assessments SET maximum_marks = 40 WHERE assessment_code = 'CAT1'")
    monkeypatch.setattr(assessment_config, 'load_config', lambda: stale)
    with pytest.raises(ValidationError, match='between 0 and 40'):
        marks_service.save_marks(marks_world['admin'], marks_world['algo'],
                                 {marks_world['ann']: {'CAT1': Decimal(45)}})
    assert execute_query('SELECT 1 FROM assessment_marks') == []


def mark_id(world):
    return execute_query('SELECT assessment_mark_id AS id FROM assessment_marks')[0]['id']


def test_the_audit_old_value_comes_from_the_locked_row_not_an_earlier_read(marks_world, monkeypatch):
    record_mark(marks_world['ann'], marks_world['algo'], 'CAT1', 42)
    real_get = marks_service.get_mark

    def stale_get(user, mark_id):
        mark = real_get(user, mark_id)
        mark['marks_obtained'] = Decimal(40)                       # what a slow earlier read might have seen
        return mark
    monkeypatch.setattr(marks_service, 'get_mark', stale_get)
    marks_service.change_mark(marks_world['admin'], mark_id(marks_world), Decimal(45))
    assert '42 -> 45' in audit.recent(1)[0]['detail']


def test_deleting_a_mark_that_vanished_is_reported_and_not_audited(marks_world, monkeypatch):
    record_mark(marks_world['ann'], marks_world['algo'], 'CAT1', 42)
    target = mark_id(marks_world)
    real_load = marks_service._load_mark

    def load_then_vanish(user, assessment_mark_id):
        mark = real_load(user, assessment_mark_id)
        execute_update('DELETE FROM assessment_marks WHERE assessment_mark_id = %s', (assessment_mark_id,))
        return mark
    monkeypatch.setattr(marks_service, '_load_mark', load_then_vanish)
    with pytest.raises(LookupError):
        marks_service.delete_mark(marks_world['admin'], target)
    assert audit.count() == 0


def test_a_deadlock_shows_a_try_again_page_not_a_crash(app, sign_in, monkeypatch):
    admin = sign_in('admin')
    with app.app_context():
        subject = make_subject()

    def deadlock(*args, **kwargs):
        raise mysql.connector.Error(msg='Deadlock found when trying to get lock', errno=1213)
    monkeypatch.setattr(marks_service, 'save_marks', deadlock)
    response = post(admin.client, f'/assessments/subjects/{subject}', {})
    assert response.status_code == 409
    assert b'try again' in response.data.lower() and b'Deadlock' not in response.data


# ---- the last administrator, under concurrency ------------------------------

def test_two_administrators_cannot_deactivate_each_other_at_the_same_moment(app):
    with app.app_context():
        first, second = make_user('first', 'admin'), make_user('second', 'admin')
    for _ in range(6):
        with app.app_context():
            execute_update('UPDATE users SET is_active = 1')
        outcomes, gate = [], threading.Barrier(2)

        def deactivate(target):
            with app.app_context():
                gate.wait()
                try:
                    auth_service.set_active(target, False)
                    outcomes.append('done')
                except ValidationError:
                    outcomes.append('refused')

        threads = [threading.Thread(target=deactivate, args=(second,)),
                   threading.Thread(target=deactivate, args=(first,))]
        [t.start() for t in threads]
        [t.join() for t in threads]
        with app.app_context():
            active = execute_query('SELECT COUNT(*) AS n FROM users WHERE is_active = 1')[0]['n']
        assert active == 1, outcomes
        assert sorted(outcomes) == ['done', 'refused']


# ---- audit failures must not undo or hide a completed change ----------------

def test_a_failed_audit_write_is_logged_and_does_not_raise(ctx, monkeypatch, caplog):
    class Broken:
        def __enter__(self):
            raise mysql.connector.Error(msg='audit table is locked', errno=1205)

        def __exit__(self, *exc):
            return False
    monkeypatch.setattr(audit, 'transaction', lambda: Broken())
    with caplog.at_level(logging.ERROR):
        audit.record(None, 'x.y', 'thing')
    assert 'Audit write failed' in caplog.text


def test_a_failed_audit_write_inside_a_callers_transaction_still_fails_the_transaction(ctx):
    from db import transaction
    with pytest.raises(mysql.connector.Error):
        with transaction() as cursor:
            cursor.execute('DROP TABLE audit_log_does_not_exist_zz')


def test_account_creation_still_shows_the_password_if_the_audit_write_fails(app, sign_in, monkeypatch):
    admin = sign_in('admin')

    class Broken:
        def __enter__(self):
            raise mysql.connector.Error(msg='locked', errno=1205)

        def __exit__(self, *exc):
            return False
    monkeypatch.setattr(audit, 'transaction', lambda: Broken())
    response = post(admin.client, '/admin/users/new', {'username': 'newbie', 'role': 'admin'})
    assert response.status_code == 200 and b'temporary-password' in response.data


# ---- fail-closed access registry --------------------------------------------

def test_a_route_missing_from_the_registry_is_denied_not_opened_to_everyone(app, sign_in):
    app.add_url_rule('/rogue', 'rogue', lambda: 'secret')
    admin = sign_in('admin')
    assert admin.client.get('/rogue').status_code == 403


# ---- request size and password-check throttling -----------------------------

def test_oversized_requests_are_refused_politely(app, sign_in):
    admin = sign_in('admin')
    response = admin.client.post('/students/add', data={'csrf_token': csrf(admin.client),
                                                        'full_name': 'x' * 2_000_000})
    assert response.status_code == 413 and b'Traceback' not in response.data


def test_the_current_password_check_cannot_be_guessed_at_forever(app, sign_in):
    admin = sign_in('admin')
    attempt = lambda guess: post(admin.client, '/account/password', {
        'current_password': guess, 'new_password': 'Brand-New-Pass-77', 'confirm_password': 'Brand-New-Pass-77'})
    for _ in range(5):
        assert b'incorrect' in attempt('wrong-guess-12').data
    blocked = attempt(PASSWORD)                                   # even the right one is refused now
    assert b'Too many' in blocked.data
    with app.app_context():
        assert auth_service.authenticate(admin.username, PASSWORD) is not None


def test_student_delete_warns_that_marks_go_with_the_student():
    import pathlib
    source = (pathlib.Path(__file__).resolve().parent.parent / 'templates' / 'students.html').read_text()
    assert 'data-confirm="Delete {{ student.full_name }} and ALL of their marks' in source
