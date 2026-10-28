"""Append-only record of who changed what. Never put passwords or hashes in `detail`."""
import logging

from mysql.connector import Error as MySQLError

from db import DatabaseUnavailable, execute_query, like_contains, transaction

logger = logging.getLogger(__name__)

DETAIL_LIMIT = 500


def record(user, action, entity, entity_id=None, detail=None, ip=None, cursor=None):
    """Write one entry.

    With `cursor` the entry is part of the caller's transaction: if it fails, the change fails too.
    Without one it is written on its own, after the change; a failure is then logged and swallowed
    so that a completed change (or a one-time password the caller must still show) is not lost.
    """
    user_id = user['user_id'] if user else None
    username = user['username'] if user else None
    detail = detail[:DETAIL_LIMIT] if detail else None
    values = (user_id, username, action, entity,
              None if entity_id is None else str(entity_id), detail, ip)
    statement = ('INSERT INTO audit_log (user_id, username, action, entity, entity_id, detail, '
                 'ip_address) VALUES (%s, %s, %s, %s, %s, %s, %s)')
    if cursor is not None:
        cursor.execute(statement, values)
        return
    try:
        with transaction() as own:
            own.execute(statement, values)
    except (MySQLError, DatabaseUnavailable):
        logger.error('Audit write failed for %s on %s %s', action, entity, entity_id)


def _match(search):
    if not search:
        return '', ()
    pattern = like_contains(search)
    return (' WHERE action LIKE %s OR username LIKE %s OR entity LIKE %s OR detail LIKE %s',
            (pattern,) * 4)


def count(search=None):
    where, params = _match(search)
    return execute_query(f'SELECT COUNT(*) AS n FROM audit_log{where}', params)[0]['n']


def recent(limit, offset=0, search=None):
    where, params = _match(search)
    return execute_query(f'SELECT * FROM audit_log{where} ORDER BY audit_id DESC LIMIT %s OFFSET %s',
                         (*params, limit, offset))
