import shutil
from pathlib import Path

import pytest
from sqlalchemy.orm import Session, sessionmaker

from friday.core.instruments.download import FolderFetcher
from friday.core.instruments.refresh import SourceResult, refresh_instruments

FIXTURES = Path(__file__).parents[1] / "fixtures" / "instruments"


@pytest.fixture
def lists(tmp_path: Path) -> Path:
    """A writable copy of the fixture lists: slices of the real files from 2026-10-24."""
    folder = tmp_path / "lists"
    shutil.copytree(FIXTURES, folder)
    return folder


@pytest.fixture
def refresh(factory: sessionmaker[Session], lists: Path):
    def run(*sources: str) -> dict[str, SourceResult]:
        results = refresh_instruments(
            factory, FolderFetcher(lists), sources or ("nse", "amfi", "us")
        )
        return {result.source: result for result in results}

    return run


@pytest.fixture
def edit_list(lists: Path):
    """Change part of a fixture list, as a later download would. ``new=""`` drops it."""

    def edit(file: str, old: str, new: str) -> None:
        path = lists / file
        text = path.read_text(encoding="utf-8")
        assert old in text, f"{old!r} not in {file}"
        path.write_text(text.replace(old, new), encoding="utf-8")

    return edit
