"""Database backups with mysqldump.

The password reaches mysqldump through the MYSQL_PWD environment variable, so it
never appears in the command line, shell history or process list arguments.
"""
import os
import subprocess
from datetime import datetime
from pathlib import Path


class BackupError(RuntimeError):
    """The backup could not be made or did not pass verification."""


def _verify(path):
    if path.stat().st_size == 0:
        raise BackupError('mysqldump produced an empty file.')
    with path.open('rb') as handle:
        if b'CREATE TABLE' not in handle.read():
            raise BackupError('The file does not look like a database dump (no CREATE TABLE found).')


def run_backup(config, output_dir, mysqldump='mysqldump', now=None):
    """Dump the configured database into `output_dir` and verify the result. Returns the path."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = (now or datetime.now()).strftime('%Y%m%d_%H%M%S')
    path = output_dir / f"{config['DB_NAME']}_{stamp}.sql"
    command = [mysqldump, '--host', str(config['DB_HOST']), '--port', str(config['DB_PORT']),
               '--user', config['DB_USER'], '--single-transaction', '--routines', '--no-tablespaces',
               config['DB_NAME']]
    environment = dict(os.environ, MYSQL_PWD=config['DB_PASSWORD'])

    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, 'wb') as handle:
            result = subprocess.run(command, env=environment, stdout=handle,
                                    stderr=subprocess.PIPE, check=False)
        if result.returncode != 0:
            message = result.stderr.decode('utf-8', 'replace').strip() or f'exit code {result.returncode}'
            raise BackupError(f'mysqldump failed: {message}')
        _verify(path)
    except FileNotFoundError as error:
        path.unlink(missing_ok=True)
        raise BackupError(f'Could not run "{mysqldump}". Install the MySQL client tools or '
                          'pass the full path with --mysqldump.') from error
    except BackupError:
        path.unlink(missing_ok=True)
        raise
    return path
