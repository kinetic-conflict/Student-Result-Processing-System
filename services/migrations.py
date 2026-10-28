"""Ordered, tracked, additive schema migrations.

Each file in database/migrations runs once and is recorded in
`schema_migrations`. A failed file stops the run and is not recorded.
MySQL cannot roll back DDL, so take a backup before applying (see README).
"""
from pathlib import Path

import mysql.connector

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / 'database' / 'migrations'
REQUIRED_TABLES = ('students', 'subjects', 'examinations', 'marks',
                   'users', 'assessments', 'assessment_marks')


class MigrationError(RuntimeError):
    """A migration could not run. The message says what to do next."""


def _fetch_column(connection, query):
    cursor = connection.cursor()
    try:
        cursor.execute(query)
        return {row[0] for row in cursor.fetchall()}
    finally:
        cursor.close()


def _applied_versions(connection):
    if 'schema_migrations' not in _fetch_column(connection, 'SHOW TABLES'):
        return set()
    return _fetch_column(connection, 'SELECT version FROM schema_migrations')


def pending_migrations(connection, directory=MIGRATIONS_DIR):
    """Migration files not yet applied, in order. Read-only."""
    applied = _applied_versions(connection)
    return [path for path in sorted(Path(directory).glob('*.sql')) if path.stem not in applied]


def _require_base_schema(connection):
    missing = [t for t in REQUIRED_TABLES if t not in _fetch_column(connection, 'SHOW TABLES')]
    if missing:
        raise MigrationError(
            'Base tables are missing (' + ', '.join(missing) + '). On a new install run '
            'database/schema.sql and then database/migration_add_assessments.sql first.'
        )


def _run_file(connection, path):
    cursor = connection.cursor()
    try:
        for result in cursor.execute(path.read_text(encoding='utf-8'), multi=True):
            if result.with_rows:
                result.fetchall()
        connection.commit()
    except mysql.connector.Error as error:
        raise MigrationError(f'Migration {path.stem} failed: {error.msg}') from error
    finally:
        cursor.close()


def apply_pending(connection, directory=MIGRATIONS_DIR):
    """Apply every pending migration in order. Returns the versions applied."""
    _require_base_schema(connection)
    cursor = connection.cursor()
    cursor.execute(
        'CREATE TABLE IF NOT EXISTS schema_migrations ('
        'version VARCHAR(100) PRIMARY KEY, '
        'applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP) ENGINE=InnoDB'
    )
    cursor.close()

    applied = []
    for path in pending_migrations(connection, directory):
        _run_file(connection, path)
        cursor = connection.cursor()
        cursor.execute('INSERT INTO schema_migrations (version) VALUES (%s)', (path.stem,))
        connection.commit()
        cursor.close()
        applied.append(path.stem)
    return applied
