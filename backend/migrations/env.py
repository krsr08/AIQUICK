"""Migration connection comes from caller or an administrator-only environment URL."""
import os

from alembic import context
from sqlalchemy import create_engine, pool
from autoqa.persistence.schema import metadata

config = context.config


def migrate(connection):
    context.configure(connection=connection, target_metadata=metadata, include_schemas=True)
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    raise RuntimeError("Offline migrations are disabled; use a verified PostgreSQL admin connection.")
elif config.attributes.get("connection") is not None:
    migrate(config.attributes["connection"])
else:
    migration_url = os.environ.get("AUTOQA_MIGRATION_URL")
    if not migration_url:
        raise RuntimeError("AUTOQA_MIGRATION_URL or an explicit connection is required.")
    engine = create_engine(migration_url, poolclass=pool.NullPool, echo=False, hide_parameters=True)
    try:
        with engine.connect() as connection:
            migrate(connection)
    finally:
        engine.dispose()
