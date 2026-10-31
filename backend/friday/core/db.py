"""SQLite engine, sessions and migrations."""

import shutil
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from friday.config import BACKEND_DIR, REPO_ROOT, Settings


class Base(DeclarativeBase):
    """Base class for all ORM models."""


def _apply_pragmas(dbapi_connection: Any, _record: Any) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")  # the UI can read while jobs write
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA busy_timeout=5000")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.close()


def move_old_data(old: Path, new: Path) -> bool:
    """Move the data folder Friday used to keep in the repo to where it lives now, once.
    Only when the new folder has no database yet, so nothing there is overwritten."""
    if not (old / "friday.db").exists() or (new / "friday.db").exists():
        return False
    new.mkdir(parents=True, exist_ok=True)
    for item in old.iterdir():
        shutil.move(item, new / item.name)
    old.rmdir()
    return True


def _prepare(settings: Settings) -> None:
    if settings.data_dir == Settings.model_fields["data_dir"].default:
        move_old_data(REPO_ROOT / "data", settings.data_dir)
    settings.data_dir.mkdir(parents=True, exist_ok=True)


def make_engine(settings: Settings) -> Engine:
    _prepare(settings)
    engine = create_engine(
        settings.database_url,
        connect_args={"check_same_thread": False},
    )
    event.listen(engine, "connect", _apply_pragmas)
    return engine


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False)


@contextmanager
def session_scope(factory: sessionmaker[Session]) -> Iterator[Session]:
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def alembic_config(settings: Settings) -> Config:
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "migrations"))
    config.set_main_option("sqlalchemy.url", settings.database_url)
    config.attributes["configure_logger"] = False  # keep the app's own logging setup
    return config


def upgrade_database(settings: Settings) -> None:
    """Bring the database schema up to the latest migration. Safe to run repeatedly."""
    _prepare(settings)
    command.upgrade(alembic_config(settings), "head")
