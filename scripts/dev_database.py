"""Persistent Windows demo PostgreSQL; credentials are protected by user-bound DPAPI."""
from contextlib import contextmanager
import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import secrets
import socket

from scripts.local_postgres import ROOT, DEFAULT_BIN, _run, grant_owner_access

def protect(data, *, decrypt=False):
    if os.name != 'nt':
        raise RuntimeError('Configure AUTOQA_DATABASE_URL on non-Windows hosts')
    class Blob(ctypes.Structure):
        _fields_ = [('size', wintypes.DWORD), ('data', ctypes.POINTER(ctypes.c_ubyte))]
    buffer = ctypes.create_string_buffer(data)
    source = Blob(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte)))
    output = Blob()
    crypt = ctypes.WinDLL('crypt32', use_last_error=True)
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.LocalFree.argtypes = [ctypes.c_void_p]
    function = crypt.CryptUnprotectData if decrypt else crypt.CryptProtectData
    function.argtypes = [ctypes.POINTER(Blob), ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p,
                         ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(Blob)]
    if not function(ctypes.byref(source), None, None, None, None, 1, ctypes.byref(output)):
        raise RuntimeError('OS credential protection failed')
    try:
        return ctypes.string_at(output.data, output.size)
    finally:
        kernel.LocalFree(output.data)

@contextmanager
def dev_database(directory=None):
    from sqlalchemy import create_engine, text
    from sqlalchemy.engine import URL
    from psycopg import sql
    from alembic import command
    from alembic.config import Config
    work = (ROOT / 'work').resolve()
    directory = Path(directory).resolve() if directory is not None else work / 'dev-postgres'
    if directory.parent != work or not (directory.name == 'dev-postgres' or directory.name.startswith('autoqa-dev-test-')):
        raise ValueError('Private database directory must be an owned direct child of repository work')
    directory.mkdir(parents=True, exist_ok=True)
    # Exclusive launcher lock avoids concurrent initialization/start on the same cluster.
    lock_path = directory / 'launcher.lock'
    try:
        lock = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        raise RuntimeError('Local database launcher is already active; inspect work/dev-postgres/launcher.lock') from None
    attempted_start = False
    data = directory / 'data'
    binaries = Path(os.environ.get('AUTOQA_POSTGRES_BIN', str(DEFAULT_BIN)))
    pg_ctl = binaries / 'pg_ctl.exe'
    try:
        marker = directory / '.autoqa-owned-cluster'
        identity = 'AutoQA private development PostgreSQL v1'
        if marker.exists():
            if marker.read_text(encoding='utf-8') != identity:
                raise RuntimeError('Unrecognized private database ownership marker')
        elif any(child.name != 'launcher.lock' for child in directory.iterdir()):
            raise RuntimeError('Directory contains unrelated data; refusing to use it')
        else:
            marker.write_text(identity, encoding='utf-8')
        grant_owner_access(directory)
        secret_file = directory / 'credentials.dpapi'
        if not secret_file.exists():
            if data.exists():
                raise RuntimeError('Existing cluster has no protected credentials; refusing to overwrite')
            credentials = {'admin': secrets.token_urlsafe(32), 'runtime': secrets.token_urlsafe(32)}
            secret_file.write_bytes(protect(json.dumps(credentials).encode()))
        else:
            credentials = json.loads(protect(secret_file.read_bytes(), decrypt=True))
        if set(credentials) != {'admin', 'runtime'} or any(not isinstance(value, str) or len(value) < 32 for value in credentials.values()):
            raise RuntimeError('Invalid protected database credentials')
        if not data.exists():
            pwfile = directory / 'init-password'
            try:
                pwfile.write_text(credentials['admin'] + '\n', encoding='utf-8')
                _run([binaries / 'initdb.exe', '-D', data, '-U', 'autoqa_admin', '--pwfile', pwfile,
                      '--auth-host=scram-sha-256', '--auth-local=scram-sha-256', '--encoding=UTF8', '--no-locale'])
            finally:
                pwfile.unlink(missing_ok=True)
        if (data / 'postmaster.pid').exists():
            raise RuntimeError('The private demo cluster is already running; refusing to take ownership')
        with socket.socket() as reservation:
            reservation.bind(('127.0.0.1', 0))
            port = reservation.getsockname()[1]
        attempted_start = True
        _run([pg_ctl, '-D', data, '-l', directory / 'postgres.log', '-o',
              f'-h 127.0.0.1 -p {port}', '-w', '-t', '30', 'start'], timeout=40)
        admin = URL.create('postgresql+psycopg', username='autoqa_admin', password=credentials['admin'],
                           host='127.0.0.1', port=port, database='postgres')
        engine = create_engine(admin, isolation_level='AUTOCOMMIT', hide_parameters=True, connect_args={'connect_timeout': 5})
        try:
            with engine.connect() as connection:
                if not connection.execute(text("SELECT 1 FROM pg_database WHERE datname='autoqa'")).scalar():
                    connection.execute(text('CREATE DATABASE autoqa'))
                if not connection.execute(text("SELECT 1 FROM pg_roles WHERE rolname='autoqa_app'")).scalar():
                    with connection.connection.driver_connection.cursor() as cursor:
                        cursor.execute(sql.SQL('CREATE ROLE autoqa_app LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS PASSWORD {}').format(sql.Literal(credentials['runtime'])))
        finally:
            engine.dispose()
        engine = create_engine(admin.set(database='autoqa'), hide_parameters=True, connect_args={'connect_timeout': 5})
        try:
            config = Config(str(ROOT / 'backend' / 'alembic.ini'))
            with engine.begin() as connection:
                config.attributes['connection'] = connection
                command.upgrade(config, 'head')
        finally:
            engine.dispose()
        runtime = admin.set(database='autoqa', username='autoqa_app', password=credentials['runtime'])
        yield runtime.render_as_string(hide_password=False)
    finally:
        try:
            if attempted_start and (data / 'postmaster.pid').exists():
                try:
                    _run([pg_ctl, '-D', data, '-m', 'fast', '-w', '-t', '30', 'stop'], timeout=40)
                except RuntimeError:
                    _run([pg_ctl, '-D', data, '-m', 'immediate', '-w', '-t', '30', 'stop'], timeout=40)
        finally:
            os.close(lock)
            lock_path.unlink(missing_ok=True)
