import pytest

from services import audit
from tests.factories import make_user


def test_the_audit_log_page_lists_newest_first_and_searches(app, sign_in):
    admin = sign_in('admin')
    with app.app_context():
        audit.record(None, 'alpha.event', 'thing', 1, 'first detail')
        audit.record(None, 'beta.event', 'thing', 2, 'second detail')
    page = admin.client.get('/admin/audit').data
    assert page.index(b'beta.event') < page.index(b'alpha.event')
    found = admin.client.get('/admin/audit?search=alpha').data
    assert b'alpha.event' in found and b'beta.event' not in found
    assert admin.client.get('/admin/audit?page=junk&search=%25').status_code == 200


def test_the_audit_log_pages(app, sign_in):
    admin = sign_in('admin')
    with app.app_context():
        for index in range(30):
            audit.record(None, f'bulk.{index:02}', 'thing')
    assert b'bulk.29' in admin.client.get('/admin/audit').data
    assert b'bulk.00' in admin.client.get('/admin/audit?page=2').data


def test_only_administrators_read_the_log(sign_in):
    for role in ('faculty', 'student'):
        assert sign_in(role).client.get('/admin/audit').status_code == 403


def test_search_matches_wildcards_literally(ctx):
    audit.record(None, 'plain', 'x', detail='100% done')
    assert audit.count(search='%') == 1
    assert audit.count(search='_') == 0
