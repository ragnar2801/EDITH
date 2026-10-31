"""Tracking and syncing NAVs: history once, then only what's missing."""

import json
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from friday.core.db import session_scope
from friday.core.instruments.download import FetchError
from friday.core.instruments.models import Instrument
from friday.core.navs.models import FundNav, NavSync
from friday.core.navs.service import (
    NotAFund,
    NotTracked,
    nav_series,
    nav_stats,
    sync_navs,
    track,
    tracking_reasons,
    untrack,
)

from .conftest import NIFTY, PARAG, FakeNavFetcher


def track_codes(factory: sessionmaker[Session], funds: dict[str, int], *codes: str) -> None:
    with session_scope(factory) as session:
        for code in codes:
            track(session, session.get(Instrument, funds[code]))


def nav_count(factory: sessionmaker[Session], instrument_id: int) -> int:
    with session_scope(factory) as session:
        return session.scalar(
            select(func.count()).select_from(FundNav).where(FundNav.instrument_id == instrument_id)
        )


def drop_newest(text: str, count: int) -> str:
    body = json.loads(text)
    body["data"] = body["data"][count:]
    return json.dumps(body)


def test_first_sync_stores_the_whole_history_and_a_second_adds_nothing(
    factory, funds, fetcher: FakeNavFetcher
) -> None:
    track_codes(factory, funds, PARAG, NIFTY)

    first = sync_navs(factory, fetcher)
    second = sync_navs(factory, fetcher)

    assert first.status == "ok"
    assert {r.name: (r.status, r.added) for r in first.results} == {
        "Parag Parikh Flexi Cap Fund": ("ok", 13),
        "UTI Nifty 50 Index Fund": ("ok", 13),
    }
    assert all(r.last_date == date(2026, 10, 23) for r in first.results)
    assert second.status == "ok" and second.added == 0
    assert all((r.added, r.corrected) == (0, 0) for r in second.results)
    assert "latest" not in fetcher.calls  # AMFI's file is only fetched when needed
    with session_scope(factory) as session:
        runs = session.scalars(select(NavSync).order_by(NavSync.id)).all()
        assert [(run.status, run.added) for run in runs] == [("ok", 26), ("ok", 0)]


def test_missed_days_are_filled_exactly(factory, funds, fetcher: FakeNavFetcher) -> None:
    track_codes(factory, funds, PARAG)
    full = fetcher.history_text[PARAG]
    fetcher.history_text[PARAG] = drop_newest(full, 3)  # three days away from the laptop
    sync_navs(factory, fetcher)
    assert nav_count(factory, funds[PARAG]) == 10

    fetcher.history_text[PARAG] = full
    result = sync_navs(factory, fetcher)

    assert result.results[0].added == 3
    assert nav_count(factory, funds[PARAG]) == 13


def test_a_corrected_nav_is_updated_in_place(factory, funds, fetcher: FakeNavFetcher) -> None:
    track_codes(factory, funds, PARAG)
    sync_navs(factory, fetcher)
    fetcher.history_text[PARAG] = fetcher.history_text[PARAG].replace("88.96950", "88.97010")

    result = sync_navs(factory, fetcher)

    assert (result.results[0].added, result.results[0].corrected) == (0, 1)
    with session_scope(factory) as session:
        assert nav_series(session, funds[PARAG])[-1] == (date(2026, 10, 23), Decimal("88.9701"))


def test_when_mfapi_fails_the_latest_nav_comes_from_amfi(
    factory, funds, fetcher: FakeNavFetcher
) -> None:
    track_codes(factory, funds, PARAG, NIFTY)
    fetcher.history_text[NIFTY] = FetchError("https://api.mfapi.in/mf/120716: HTTP 502")

    result = sync_navs(factory, fetcher)

    nifty = next(r for r in result.results if r.instrument_id == funds[NIFTY])
    assert (nifty.status, nifty.added, nifty.last_date) == ("fallback", 1, date(2026, 10, 23))
    assert "HTTP 502" in nifty.message
    assert result.status == "ok"  # every fund has its latest NAV
    with session_scope(factory) as session:
        assert nav_series(session, funds[NIFTY]) == [(date(2026, 10, 23), Decimal("159.177"))]
        source = session.scalar(select(FundNav.source).where(FundNav.instrument_id == funds[NIFTY]))
        assert source == "amfi"


def test_a_fund_that_fails_everywhere_does_not_stop_the_others(
    factory, funds, fetcher: FakeNavFetcher
) -> None:
    track_codes(factory, funds, PARAG, NIFTY)
    fetcher.history_text[NIFTY] = FetchError("timeout")
    fetcher.latest_text = FetchError("AMFI down")

    result = sync_navs(factory, fetcher)

    assert result.status == "partial"
    nifty = next(r for r in result.results if r.instrument_id == funds[NIFTY])
    assert nifty.status == "failed" and "AMFI down" in nifty.message
    assert nav_count(factory, funds[PARAG]) == 13


def test_everything_failing_is_a_failed_run(factory, funds, fetcher: FakeNavFetcher) -> None:
    track_codes(factory, funds, PARAG)
    fetcher.history_text[PARAG] = "<html>Service unavailable</html>"
    fetcher.latest_text = FetchError("offline")

    assert sync_navs(factory, fetcher).status == "failed"


def test_syncing_an_untracked_fund_is_refused(factory, funds, fetcher) -> None:
    with pytest.raises(NotTracked):
        sync_navs(factory, fetcher, [funds[PARAG]])


def test_only_funds_can_be_tracked(factory, funds) -> None:
    with session_scope(factory) as session, pytest.raises(NotAFund):
        track(session, session.get(Instrument, funds["INFY"]))


def test_untracking_keeps_the_navs(factory, funds, fetcher) -> None:
    track_codes(factory, funds, PARAG)
    sync_navs(factory, fetcher)
    with session_scope(factory) as session:
        untrack(session, session.get(Instrument, funds[PARAG]))
        assert tracking_reasons(session) == {}
    assert nav_count(factory, funds[PARAG]) == 13


def test_eight_place_navs_round_trip_exactly(factory, funds) -> None:
    with session_scope(factory) as session:
        session.add(
            FundNav(
                instrument_id=funds["108844"],
                nav_date=date(2017, 2, 17),
                nav=Decimal("14.86269632"),
                source="amfi",
            )
        )
    with session_scope(factory) as session:
        assert nav_series(session, funds["108844"]) == [(date(2017, 2, 17), Decimal("14.86269632"))]


def test_nav_stats_by_hand() -> None:
    points = [
        (date(2023, 10, 20), Decimal("50")),
        (date(2025, 10, 23), Decimal("80")),  # the last NAV a year or more before the latest
        (date(2025, 11, 3), Decimal("72")),  # 52-week low
        (date(2026, 6, 1), Decimal("95")),  # 52-week high
        (date(2026, 10, 22), Decimal("89.4088")),
        (date(2026, 10, 23), Decimal("88.9695")),
    ]

    stats = nav_stats(points)

    assert stats.latest == (date(2026, 10, 23), Decimal("88.9695"))
    assert stats.change_1d_pct == Decimal("-0.49")  # 88.9695 / 89.4088 - 1 = -0.4913%
    assert stats.change_1y_pct == Decimal("11.21")  # 88.9695 / 80 - 1 = 11.2119%
    assert stats.change_since_first_pct == Decimal("77.94")  # 88.9695 / 50 - 1
    # (88.9695 / 50) ^ (365 / 1099 days) - 1 = 21.0933% a year
    assert stats.cagr_pct == Decimal("21.09")
    assert stats.high_52w == (date(2026, 6, 1), Decimal("95"))
    assert stats.low_52w == (date(2025, 11, 3), Decimal("72"))


def test_nav_stats_for_a_short_history_have_no_cagr_or_year_change() -> None:
    stats = nav_stats([(date(2026, 10, 23), Decimal("10"))])

    assert (stats.change_1d_pct, stats.change_1y_pct, stats.cagr_pct) == (None, None, None)
    assert stats.change_since_first_pct == Decimal("0.00")
    assert nav_stats([]) is None
