import json
import stat
import sys

import pytest

from tests.conftest import app_settings

STUB = f"""#!{sys.executable}
import json, os, sys
with open(os.environ['STUB_ARGS_FILE'], 'w') as handle:
    json.dump({{'argv': sys.argv[1:], 'pwd': os.environ.get('MYSQL_PWD')}}, handle)
mode = os.environ.get('STUB_MODE', 'ok')
if mode == 'ok':
    print('-- dump')
    print('CREATE TABLE t (id int);')
    print('INSERT INTO t VALUES (1);')
elif mode == 'junk':
    print('-- no tables here')
elif mode == 'fail':
    sys.stderr.write('mysqldump: Got error: 1045: Access denied')
    sys.exit(2)
"""


@pytest.fixture
def stub(tmp_path, monkeypatch):
    path = tmp_path / 'fake_mysqldump'
    path.write_text(STUB)
    path.chmod(0o755)
    monkeypatch.setenv('STUB_ARGS_FILE', str(tmp_path / 'args.json'))
    return path


def received(tmp_path):
    return json.loads((tmp_path / 'args.json').read_text())


def run_backup(app, stub, tmp_path):
    return app.test_cli_runner().invoke(
        args=['backup', '--output-dir', str(tmp_path / 'out'), '--mysqldump', str(stub)])


def test_backup_writes_a_private_verified_file(app, stub, tmp_path):
    result = run_backup(app, stub, tmp_path)
    assert result.exit_code == 0, result.output
    (dump,) = (tmp_path / 'out').glob('*.sql')
    assert dump.name.startswith(app.config['DB_NAME'])
    assert b'CREATE TABLE' in dump.read_bytes()
    assert stat.S_IMODE(dump.stat().st_mode) == 0o600          # personal data: owner only
    assert str(dump) in result.output and 'bytes' in result.output


def test_the_password_goes_through_the_environment_never_the_command_line(app, stub, tmp_path):
    result = run_backup(app, stub, tmp_path)
    seen = received(tmp_path)
    password = app.config['DB_PASSWORD']
    assert seen['pwd'] == password
    assert not any(password in argument for argument in seen['argv'])
    assert password not in result.output
    assert app.config['DB_NAME'] in seen['argv']


def test_an_empty_dump_is_rejected_and_removed(app, stub, tmp_path, monkeypatch):
    monkeypatch.setenv('STUB_MODE', 'empty')
    result = run_backup(app, stub, tmp_path)
    assert result.exit_code != 0 and 'empty' in result.output
    assert list((tmp_path / 'out').glob('*.sql')) == []


def test_a_dump_without_tables_is_rejected(app, stub, tmp_path, monkeypatch):
    monkeypatch.setenv('STUB_MODE', 'junk')
    result = run_backup(app, stub, tmp_path)
    assert result.exit_code != 0 and 'does not look like' in result.output
    assert list((tmp_path / 'out').glob('*.sql')) == []


def test_a_failing_mysqldump_is_reported_without_secrets(app, stub, tmp_path, monkeypatch):
    monkeypatch.setenv('STUB_MODE', 'fail')
    result = run_backup(app, stub, tmp_path)
    assert result.exit_code != 0 and 'Access denied' in result.output
    assert app.config['DB_PASSWORD'] not in result.output
    assert list((tmp_path / 'out').glob('*.sql')) == []


def test_a_missing_mysqldump_explains_what_to_do(app, tmp_path):
    result = app.test_cli_runner().invoke(
        args=['backup', '--output-dir', str(tmp_path), '--mysqldump', str(tmp_path / 'nope')])
    assert result.exit_code != 0 and '--mysqldump' in result.output
