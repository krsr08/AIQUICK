"""Isolated, disposable PostgreSQL for local integration tests; never uses a service."""
from contextlib import contextmanager
import os
from pathlib import Path
import secrets
import shutil
import socket
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / 'work'
DEFAULT_BIN = Path(r'C:\Program Files\PostgreSQL\18\bin')

def grant_owner_access(directory):
    """Give the current identity explicit access after PostgreSQL drops admin groups."""
    if os.name == 'nt':
        identity = subprocess.check_output(['whoami.exe'], text=True, timeout=10).strip()
        _run(['icacls.exe', directory, '/grant', identity + ':(OI)(CI)F'], timeout=10)


def _run(arguments, timeout=90):
    options = {'creationflags': subprocess.CREATE_NO_WINDOW} if os.name == 'nt' else {}
    try:
        diagnostics = subprocess.PIPE if Path(arguments[0]).stem == 'initdb' else subprocess.DEVNULL
        return subprocess.run([str(a) for a in arguments], check=True, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=diagnostics,
                              text=True, timeout=timeout, **options)
    except (subprocess.SubprocessError, OSError) as error:
        # Report only fixed diagnostic categories, never paths, credentials or raw output.
        diagnostic = str(getattr(error, 'stderr', '') or '').lower()
        category = next((label for needle, label in (
            ('permission denied', 'permission denied'), ('access is denied', 'access denied'),
            ('administrator', 'administrator account rejected'), ('locale', 'locale configuration'),
            ('could not open', 'file could not be opened'), ('could not execute', 'child executable failed'),
            ('invalid option', 'unsupported option'), ('unrecognized option', 'unsupported option'))
            if needle in diagnostic), 'unclassified startup failure')
        code = getattr(error, 'returncode', None)
        raise RuntimeError(f'Isolated PostgreSQL command failed: {Path(arguments[0]).name}; {category}; exit={code}') from None


@contextmanager
def local_postgres():
    """Yield a private admin SQLAlchemy URL, then stop and remove this cluster only."""
    from sqlalchemy import create_engine, text
    from sqlalchemy.engine import URL

    binaries = Path(os.environ.get('AUTOQA_POSTGRES_BIN', str(DEFAULT_BIN)))
    suffix = '.exe' if os.name == 'nt' else ''
    initdb, pg_ctl = (binaries / (name + suffix) for name in ('initdb', 'pg_ctl'))
    if not initdb.is_file() or not pg_ctl.is_file():
        raise RuntimeError('PostgreSQL initdb/pg_ctl binaries are required; set AUTOQA_POSTGRES_BIN')
    WORK.mkdir(parents=True, exist_ok=True)
    owned = Path(tempfile.mkdtemp(prefix='autoqa-pg-', dir=WORK)).resolve()
    grant_owner_access(owned)
    data = owned / 'data'
    password_file = owned / 'init-password'
    password = secrets.token_urlsafe(32)
    attempted_start = False
    stopped = True
    with socket.socket() as reservation:
        reservation.bind(('127.0.0.1', 0))
        port = reservation.getsockname()[1]
    try:
        password_file.write_text(password + '\n', encoding='utf-8')
        try:
            _run([initdb, '-D', data, '-U', 'autoqa_admin', '--pwfile', password_file,
                  '--auth-host=scram-sha-256', '--auth-local=scram-sha-256', '--encoding=UTF8', '--no-locale'])
        finally:
            password_file.unlink(missing_ok=True)
        # Explicit loopback only; pg_ctl does not install or modify Windows services.
        attempted_start = True
        _run([pg_ctl, '-D', data, '-l', owned / 'postgres.log', '-o',
              f'-h 127.0.0.1 -p {port}', '-w', '-t', '30', 'start'], timeout=40)
        admin = URL.create('postgresql+psycopg', username='autoqa_admin', password=password,
                           host='127.0.0.1', port=port, database='postgres')
        engine = create_engine(admin, isolation_level='AUTOCOMMIT')
        try:
            with engine.connect() as connection:
                connection.execute(text('CREATE DATABASE autoqa'))
        finally:
            engine.dispose()
        yield admin.set(database='autoqa').render_as_string(hide_password=False)
    finally:
        if attempted_start:
            try:
                _run([pg_ctl, '-D', data, '-m', 'immediate', '-w', '-t', '30', 'stop'], timeout=40)
            except RuntimeError:
                # Startup failure may mean no server ever existed. Never remove a live cluster.
                stopped = not (data / 'postmaster.pid').exists()
        resolved_work = WORK.resolve()
        if owned.parent != resolved_work or not owned.name.startswith('autoqa-pg-'):
            raise RuntimeError('Refusing to remove unrecognized PostgreSQL directory')
        if stopped:
            shutil.rmtree(owned)
        else:
            raise RuntimeError('Isolated PostgreSQL could not stop; retained its work directory')
