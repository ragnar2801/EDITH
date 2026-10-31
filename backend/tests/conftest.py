from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from friday.api.app import create_app
from friday.config import Settings
from friday.core.db import make_engine, make_session_factory, upgrade_database


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text('<!doctype html><div id="root"></div>', encoding="utf-8")
    (dist / "assets").mkdir()
    (dist / "assets" / "app.js").write_text("console.log('friday')", encoding="utf-8")
    return Settings(
        data_dir=tmp_path / "data",
        log_dir=tmp_path / "logs",
        frontend_dist=dist,
        fm_push=False,  # tests start their own receiver on a free port
    )


@pytest.fixture
def client(settings: Settings) -> Iterator[TestClient]:
    with TestClient(create_app(settings)) as test_client:
        yield test_client


@pytest.fixture
def factory(settings: Settings) -> Iterator[sessionmaker[Session]]:
    upgrade_database(settings)
    engine = make_engine(settings)
    yield make_session_factory(engine)
    engine.dispose()
