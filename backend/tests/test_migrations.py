"""Real PostgreSQL migration roundtrip in a separate disposable database."""
from pathlib import Path
from uuid import uuid4

from alembic import command
from alembic.config import Config
from psycopg import sql
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError

ROOT = Path(__file__).resolve().parents[2]


def test_migration_roundtrip_and_runtime_ddl_denial(database):
    database_name = 'test_migrations_' + uuid4().hex
    server = create_engine(database['admin_url'], isolation_level='AUTOCOMMIT', hide_parameters=True)
    admin = create_engine(make_url(database['admin_url']).set(database=database_name), hide_parameters=True)
    runtime = create_engine(make_url(database['runtime_url']).set(database=database_name), hide_parameters=True)
    created = False

    def migrate(operation, revision, engine=admin):
        config = Config(str(ROOT / 'backend' / 'alembic.ini'))
        with engine.begin() as connection:
            config.attributes['connection'] = connection
            operation(config, revision)

    def table_names():
        with admin.connect() as connection:
            return set(connection.execute(text("SELECT tablename FROM pg_tables WHERE schemaname='autoqa'")).scalars())

    try:
        # SQL identifiers are composable-quoted; this never targets the fixture database.
        with server.connect() as connection:
            with connection.connection.driver_connection.cursor() as cursor:
                cursor.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(database_name)))
        created = True
        migrate(command.upgrade, 'head')
        assert table_names() == {'plan_snapshots', 'approvals', 'test_runs'}
        for statement in (
            'CREATE TABLE autoqa.unauthorized (id integer)',
            'CREATE TABLE public.unauthorized (id integer)',
            'ALTER TABLE autoqa.plan_snapshots ADD COLUMN unauthorized integer',
            'TRUNCATE autoqa.plan_snapshots CASCADE',
        ):
            with pytest.raises(DBAPIError) as denied:
                with runtime.begin() as connection:
                    connection.execute(text(statement))
            assert denied.value.orig.sqlstate == '42501'
        with pytest.raises(DBAPIError) as denied:
            migrate(command.downgrade, 'base', runtime)
        assert denied.value.orig.sqlstate == '42501'
        assert table_names() == {'plan_snapshots', 'approvals', 'test_runs'}
        migrate(command.downgrade, 'base')
        assert table_names() == set()
        with admin.connect() as connection:
            assert connection.execute(text("SELECT count(*) FROM pg_namespace WHERE nspname='autoqa'")).scalar_one() == 0
            assert connection.execute(text("SELECT count(*) FROM public.alembic_version")).scalar_one() == 0
            assert not connection.execute(text("SELECT has_schema_privilege('autoqa_app', 'public', 'CREATE')")).scalar_one()
        migrate(command.upgrade, 'head')
        assert table_names() == {'plan_snapshots', 'approvals', 'test_runs'}
        with admin.connect() as connection:
            assert connection.execute(text('SELECT version_num FROM public.alembic_version')).scalar_one() == '0001_tenant_storage'
    finally:
        runtime.dispose()
        admin.dispose()
        try:
            if created:
                with server.connect() as connection:
                    with connection.connection.driver_connection.cursor() as cursor:
                        cursor.execute(sql.SQL('DROP DATABASE {}').format(sql.Identifier(database_name)))
        finally:
            server.dispose()
