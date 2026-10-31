"""Comparison figures on hand-worked series."""

from datetime import date, timedelta
from decimal import Decimal as D

import pytest

from friday.core.backtest import engine
from friday.core.compare import figures
from friday.core.compare.figures import History


def daily(start: str, values: list[float]) -> engine.Series:
    first = date.fromisoformat(start)
    return [(first + timedelta(days=i), D(str(v))) for i, v in enumerate(values)]


def steady(start: str, end: str, yearly_pct: float) -> engine.Series:
    """One NAV a day growing at ``yearly_pct`` a year."""
    first, last = date.fromisoformat(start), date.fromisoformat(end)
    days = (last - first).days
    return [
        (first + timedelta(days=i), D(str(round(10 * (1 + yearly_pct / 100) ** (i / 365), 8))))
        for i in range(days + 1)
    ]


def test_the_window_starts_at_the_youngest_fund_and_ends_at_the_last_shared_nav() -> None:
    old = History(daily("2020-01-01", [10] * 30))
    young = History(daily("2020-01-11", [10] * 25))
    empty = History([])

    found = figures.window({1: old, 2: young, 3: empty})

    assert found is not None
    assert (found.start, found.end) == (date(2020, 1, 11), date(2020, 1, 30))
    assert found.members == [1, 2]
    assert (found.limited_by, found.earliest_start) == (2, date(2020, 1, 1))


def test_leaving_the_youngest_out_starts_at_the_next_one() -> None:
    histories = {
        1: History(daily("2020-01-01", [10] * 40)),
        2: History(daily("2020-01-05", [10] * 36)),
        3: History(daily("2020-01-20", [10] * 21)),
    }

    found = figures.window(histories, start=date(2020, 1, 5))

    assert found is not None
    assert found.members == [1, 2]
    assert (found.limited_by, found.earliest_start) == (2, date(2020, 1, 1))


def test_funds_of_the_same_age_limit_nothing() -> None:
    found = figures.window(
        {1: History(daily("2020-01-01", [10] * 5)), 2: History(daily("2020-01-01", [10] * 5))}
    )

    assert found is not None
    assert found.limited_by is None


def test_funds_with_no_dates_in_common_have_no_window() -> None:
    histories = {
        1: History(daily("2020-01-01", [10] * 5)),
        2: History(daily("2021-01-01", [10] * 5)),
    }

    assert figures.window(histories) is None


def test_recovery_runs_from_the_peak_to_the_day_it_is_regained() -> None:
    dates = [date(2020, 1, d) for d in range(1, 8)]

    assert figures.recovery(dates, [100, 120, 90, 100, 121, 110, 115]) == figures.Recovery(3, True)
    assert figures.recovery(dates, [100, 120, 90, 100, 110, 110, 115]) == figures.Recovery(5, False)
    assert figures.recovery(dates, [100, 101, 102, 103, 104, 105, 106]) is None


def test_drawdowns_measure_the_fall_from_the_high() -> None:
    assert figures.drawdowns([100, 120, 90, 120]) == [0, 0, -25, 0]


def test_rolling_returns_cover_every_period_inside_the_window_and_count_wins() -> None:
    fast = steady("2015-01-01", "2020-01-01", 12)
    slow = History(steady("2015-01-01", "2020-01-01", 8))
    dates = [day for day, _ in fast]

    found = figures.rolling(dates, [nav for _, nav in fast], 3, slow)

    assert found is not None
    assert found.periods == len([day for day in dates if day >= date(2018, 1, 1)])
    assert found.median_pct == pytest.approx(12, abs=0.05)
    assert found.worst_pct == pytest.approx(12, abs=0.05)
    assert found.beat_benchmark_pct == 100


def test_a_window_shorter_than_the_period_has_no_rolling_returns() -> None:
    points = steady("2019-01-01", "2020-01-01", 10)

    assert figures.rolling([d for d, _ in points], [n for _, n in points], 3, None) is None


def test_capture_compares_the_up_and_down_months() -> None:
    # The benchmark alternates +10% and −10% months; the fund moves half as much.
    bench, fund = [D(100)], [D(100)]
    for month in range(12):
        move = D("0.10") if month % 2 == 0 else D("-0.10")
        bench.append(bench[-1] * (1 + move))
        fund.append(fund[-1] * (1 + move / 2))
    dates = [date(2020 + (m // 12), m % 12 + 1, 28) for m in range(13)]

    up, down = figures.capture(dates, fund, History(list(zip(dates, bench, strict=True))))

    assert up == pytest.approx(50)
    assert down == pytest.approx(50)


def test_trailing_returns_need_the_whole_period() -> None:
    history = History(steady("2017-06-01", "2026-06-01", 10))

    assert figures.trailing(history, date(2026, 6, 1), 1) == pytest.approx(10, abs=0.05)
    assert figures.trailing(history, date(2026, 6, 1), 5) == pytest.approx(10, abs=0.05)
    assert figures.trailing(history, date(2026, 6, 1), 10) is None


def test_calendar_years_leave_partial_years_blank_and_end_with_the_year_to_date() -> None:
    history = History(
        [
            (date(2023, 3, 1), D(10)),
            (date(2023, 12, 29), D(11)),
            (date(2024, 12, 31), D("12.1")),
            (date(2025, 6, 30), D("13.31")),
        ]
    )

    years = figures.calendar(history, date(2025, 6, 30))

    assert years[2023] is None
    assert years[2024] == pytest.approx(10)
    assert years[2025] == pytest.approx(10)
    assert list(years)[-1] == 2025 and len(years) == figures.CALENDAR_YEARS


def test_funds_that_move_together_correlate() -> None:
    import math

    a = [
        (date(2020, 1, 1) + timedelta(days=i), D(str(100 + 10 * math.sin(i / 9))))
        for i in range(200)
    ]
    b = [(day, nav * 2) for day, nav in a]
    c = [(day, D(200) - nav) for day, nav in a]
    aligned = engine.align({1: a, 2: b, 3: c})

    pairs = figures.correlation(aligned, [1, 2, 3])

    assert pairs[1, 2] == pytest.approx(1)
    assert pairs[1, 3] < -0.9
    assert pairs[2, 1] == pairs[1, 2]


def test_long_windows_are_drawn_weekly() -> None:
    points = steady("2015-01-01", "2020-01-01", 10)
    aligned = engine.align({1: points})

    found = figures.over_window(aligned, 1, 3, None)

    assert len(found.growth) < 300
    assert found.growth[0] == (date(2015, 1, 1), D("10000.00"))
    assert found.growth[-1][0] == date(2020, 1, 1)
    assert found.cagr_pct == pytest.approx(10, abs=0.05)
    assert found.sip.invested == D(10_000) * 61
