from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from friday.core.db import session_scope
from friday.core.instruments.download import FetchError, FolderFetcher
from friday.core.instruments.models import Instrument
from friday.core.instruments.refresh import refresh_instruments

FIXTURES = Path(__file__).parents[1] / "fixtures" / "navs"
PARAG = "122639"
NIFTY = "120716"


def fixture_text(name: str) -> str:
    return (FIXTURES / name).read_bytes().decode("utf-8")


class FakeNavFetcher:
    """Answers from the fixture files. ``history_text`` / ``latest_text`` override a code's
    answer; an exception value is raised instead, like a failed download."""

    def __init__(self) -> None:
        self.history_text: dict[str, str | Exception] = {
            PARAG: fixture_text(f"mfapi_{PARAG}.json"),
            NIFTY: fixture_text(f"mfapi_{NIFTY}.json"),
        }
        self.latest_text: str | Exception = fixture_text("NAVAll.txt")
        self.calls: list[str] = []

    def history(self, amfi_code: str) -> str:
        self.calls.append(f"history {amfi_code}")
        answer = self.history_text.get(amfi_code, FetchError(f"mfapi {amfi_code}: HTTP 404"))
        if isinstance(answer, Exception):
            raise answer
        return answer

    def latest(self) -> str:
        self.calls.append("latest")
        if isinstance(self.latest_text, Exception):
            raise self.latest_text
        return self.latest_text


@pytest.fixture
def funds(factory: sessionmaker[Session]) -> dict[str, int]:
    """Instruments from the NAV fixture's AMFI slice, plus one stock. Code → instrument id."""
    refresh_instruments(factory, FolderFetcher(FIXTURES), ["amfi"])
    with session_scope(factory) as session:
        now = datetime.now(UTC)
        session.add(
            Instrument(
                kind="stock",
                name="Infosys Limited",
                market="IN",
                currency="INR",
                source="nse",
                exchange="NSE",
                symbol="INFY",
                exposure="IN",
                created_at=now,
                updated_at=now,
            )
        )
        session.flush()
        rows = session.execute(select(Instrument.amfi_code, Instrument.id, Instrument.symbol)).all()
    ids = {code: instrument_id for code, instrument_id, _ in rows if code}
    ids["INFY"] = next(instrument_id for _, instrument_id, symbol in rows if symbol == "INFY")
    return ids


@pytest.fixture
def fetcher() -> FakeNavFetcher:
    return FakeNavFetcher()
