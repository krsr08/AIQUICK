"""Real PostgreSQL integration boundary shared by the test session."""
import os
from pathlib import Path
import secrets
import sys

import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from alembic import command
from alembic.config import Config

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.local_postgres import local_postgres


@pytest.fixture(scope='session', autouse=True)
def database():
    previous = os.environ.get('AUTOQA_DATABASE_URL')
    with local_postgres() as admin_url:
        password = secrets.token_urlsafe(32)
        runtime_url = make_url(admin_url).set(username='autoqa_app', password=password).render_as_string(hide_password=False)
        engine = create_engine(admin_url)
        try:
            # psycopg composables safely quote the generated password as a SQL literal.
            from psycopg import sql
            with engine.begin() as connection:
                raw = connection.connection.driver_connection
                with raw.cursor() as cursor:
                    cursor.execute(sql.SQL('CREATE ROLE autoqa_app LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS PASSWORD {}').format(sql.Literal(password)))
            config = Config(str(ROOT / 'backend' / 'alembic.ini'))
            with engine.begin() as connection:
                config.attributes['connection'] = connection
                command.upgrade(config, 'head')
            os.environ['AUTOQA_DATABASE_URL'] = runtime_url
            yield {'admin_url': admin_url, 'runtime_url': runtime_url}
        finally:
            engine.dispose()
            if previous is None:
                os.environ.pop('AUTOQA_DATABASE_URL', None)
            else:
                os.environ['AUTOQA_DATABASE_URL'] = previous
