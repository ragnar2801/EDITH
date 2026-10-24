from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from friday.api.app import create_app
from friday.config import Settings


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text('<!doctype html><div id="root"></div>', encoding="utf-8")
    (dist / "assets").mkdir()
    (dist / "assets" / "app.js").write_text("console.log('friday')", encoding="utf-8")
    return Settings(data_dir=tmp_path / "data", log_dir=tmp_path / "logs", frontend_dist=dist)


@pytest.fixture
def client(settings: Settings) -> Iterator[TestClient]:
    with TestClient(create_app(settings)) as test_client:
        yield test_client
