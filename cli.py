"""Command-line tasks: `flask --app app create-admin` and `flask --app app migrate`."""
import click
from flask.cli import with_appcontext

from db import DatabaseUnavailable, get_db_connection
from flask import current_app

from services import auth_service, migrations
from services.backup import BackupError, run_backup
from services.validation import ValidationError


@click.command('create-admin')
@click.option('--username', prompt=True, help='Login name for the new administrator.')
@click.option('--email', default=None, help='Optional email address, also usable to sign in.')
@with_appcontext
def create_admin(username, email):
    """Create an administrator. The password is typed at a hidden prompt, never passed as an argument."""
    password = click.prompt('Password', hide_input=True, confirmation_prompt=True)
    try:
        auth_service.create_user(username, auth_service.ROLE_ADMIN, email=email,
                                 password=password, must_change_password=False)
    except ValidationError as error:
        raise click.ClickException(str(error))
    click.echo(f'Administrator "{username.strip()}" created. You can sign in now.')


@click.command('migrate')
@click.option('--yes', is_flag=True, help='Skip the backup question.')
@with_appcontext
def migrate(yes):
    """Apply pending schema migrations (additive; existing rows are kept)."""
    try:
        connection = get_db_connection()
    except DatabaseUnavailable as error:
        raise click.ClickException(str(error))
    try:
        pending = migrations.pending_migrations(connection)
        if not pending:
            click.echo('Database schema is up to date.')
            return
        click.echo('Pending migrations:')
        for path in pending:
            click.echo(f'  {path.stem}')
        if not yes:
            click.confirm('MySQL cannot undo schema changes. Have you backed up the database?',
                          abort=True)
        for version in migrations.apply_pending(connection):
            click.echo(f'Applied {version}')
    except migrations.MigrationError as error:
        raise click.ClickException(str(error))
    finally:
        connection.close()


@click.command('backup')
@click.option('--output-dir', default='backups', show_default=True, help='Folder for the dump file.')
@click.option('--mysqldump', default='mysqldump', show_default=True, help='Path to the mysqldump program.')
@with_appcontext
def backup(output_dir, mysqldump):
    """Dump the database to a private, timestamped .sql file and check it is usable."""
    try:
        path = run_backup(current_app.config, output_dir, mysqldump)
    except BackupError as error:
        raise click.ClickException(str(error))
    click.echo(f'Backup written to {path} ({path.stat().st_size} bytes) and verified.')


def init_app(app):
    app.cli.add_command(create_admin)
    app.cli.add_command(migrate)
    app.cli.add_command(backup)
