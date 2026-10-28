import logging
from contextlib import contextmanager

import mysql.connector
from flask import current_app
from mysql.connector import Error

logger = logging.getLogger(__name__)

DUPLICATE_ENTRY = 1062
ROW_IS_REFERENCED = 1451
MISSING_REFERENCE = 1452


class DatabaseUnavailable(RuntimeError):
    """MySQL could not be reached. The message is safe to show to users."""


def get_db_connection():
    """Open a connection using the running app's DB_* settings."""
    config = current_app.config
    try:
        return mysql.connector.connect(
            host=config['DB_HOST'],
            port=config['DB_PORT'],
            user=config['DB_USER'],
            password=config['DB_PASSWORD'],
            database=config['DB_NAME'],
            connection_timeout=5,
        )
    except Error as error:
        logger.error('Cannot connect to MySQL at %s:%s (database %s, user %s): errno %s %s',
                     config['DB_HOST'], config['DB_PORT'], config['DB_NAME'],
                     config['DB_USER'], error.errno, error.msg)
        raise DatabaseUnavailable(
            'Could not connect to the MySQL database. Check that MySQL is running '
            'and that the DB_* settings in your .env file are correct.'
        ) from error


@contextmanager
def transaction():
    """One connection, one transaction: commit on success, roll back on any error.

    Yields a dict cursor. Statement parameters are never logged, since they can
    hold personal data.
    """
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True, buffered=True)
    try:
        yield cursor
        connection.commit()
    except BaseException as error:
        connection.rollback()
        if isinstance(error, Error):
            logger.error('Database error %s: %s', error.errno, error.msg)
        raise
    finally:
        cursor.close()
        connection.close()


def execute_query(query, params=None):
    """Run a SELECT and return all rows as dicts."""
    with transaction() as cursor:
        cursor.execute(query, params or ())
        return cursor.fetchall()


def execute_update(query, params=None):
    """Run an INSERT, UPDATE or DELETE and return the new row id (if any)."""
    with transaction() as cursor:
        cursor.execute(query, params or ())
        return cursor.lastrowid


def is_duplicate_error(error):
    """True when `error` is MySQL's duplicate-key error (errno 1062)."""
    return getattr(error, 'errno', None) == DUPLICATE_ENTRY


def is_referenced_error(error):
    """True when a delete was refused because other rows still point at the row."""
    return getattr(error, 'errno', None) == ROW_IS_REFERENCED


def is_missing_reference_error(error):
    """True when an insert or update names a parent row that does not exist."""
    return getattr(error, 'errno', None) == MISSING_REFERENCE


def like_contains(text):
    """A LIKE pattern matching rows that contain `text`, with %, _ and \\ taken literally."""
    escaped = text.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
    return f'%{escaped}%'
