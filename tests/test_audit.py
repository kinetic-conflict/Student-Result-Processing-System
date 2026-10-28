from db import execute_query, transaction
from services import audit, auth_service
from tests.factories import make_user


def entries():
    return execute_query('SELECT * FROM audit_log ORDER BY audit_id')


def test_record_stores_who_what_and_where(ctx):
    user = auth_service.get_user(make_user('boss', 'admin'))
    audit.record(user, 'mark.save', 'assessment_mark', 42, 'CAT1 40 -> 45', ip='10.0.0.7')
    (row,) = entries()
    assert (row['user_id'], row['username'], row['action'], row['entity']) == (
        user['user_id'], 'boss', 'mark.save', 'assessment_mark')
    assert (row['entity_id'], row['detail'], row['ip_address']) == ('42', 'CAT1 40 -> 45', '10.0.0.7')
    assert row['created_at'] is not None


def test_record_without_a_user_is_allowed_for_failed_logins_and_system_events(ctx):
    audit.record(None, 'login.failed', 'user', detail='unknown name')
    assert entries()[0]['user_id'] is None


def test_long_details_are_trimmed_not_rejected(ctx):
    audit.record(None, 'note', 'x', detail='y' * 900)
    assert len(entries()[0]['detail']) == 500


def test_record_can_join_the_callers_transaction(ctx):
    try:
        with transaction() as cursor:
            audit.record(None, 'inside', 'x', cursor=cursor)
            raise RuntimeError('abort the transaction')
    except RuntimeError:
        pass
    assert entries() == []


def test_recent_returns_newest_first_and_pages(ctx):
    for index in range(5):
        audit.record(None, f'action.{index}', 'x')
    assert audit.count() == 5
    assert [e['action'] for e in audit.recent(limit=2, offset=0)] == ['action.4', 'action.3']
    assert [e['action'] for e in audit.recent(limit=2, offset=4)] == ['action.0']
