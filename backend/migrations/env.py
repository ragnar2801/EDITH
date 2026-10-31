"""Alembic environment. Uses Friday's settings and ORM metadata."""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

import friday.core.tables  # noqa: F401 (registers every table on Base.metadata)
from friday.config import Settings
from friday.core.db import Base
from friday.core.instruments.search import FTS_TABLE
from friday.core.types import DecimalText, UtcDateTime

config = context.config

# Only configure logging when run from the alembic CLI, not when the app upgrades itself.
if config.config_file_name is not None and config.attributes.get("configure_logger", True):
    fileConfig(config.config_file_name, disable_existing_loggers=False)

if not config.get_main_option("sqlalchemy.url"):
    config.set_main_option("sqlalchemy.url", Settings().database_url)

target_metadata = Base.metadata


def include_name(name: str | None, type_: str, _parent_names: object) -> bool:
    """Leave the FTS5 search table and its shadow tables alone: they are created in a
    migration by hand and aren't part of the ORM metadata."""
    return not (type_ == "table" and name is not None and name.startswith(FTS_TABLE))


def render_item(type_: str, obj: object, _autogen_context: object) -> str | bool:
    """Write Friday's exact-value column types as the plain text columns they are in SQLite,
    so generated migrations don't import application code."""
    if type_ == "type" and isinstance(obj, DecimalText | UtcDateTime):
        return "sa.String()"
    return False


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        render_as_batch=True,
        include_name=include_name,
        render_item=render_item,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        # render_as_batch: SQLite can't alter columns in place, so Alembic copies the table.
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,
            include_name=include_name,
            render_item=render_item,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
