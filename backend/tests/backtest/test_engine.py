"""The backtest engine on hand-worked examples, including Friday's own tests."""

from datetime import date, timedelta
from decimal import Decimal as D

import pytest

from friday.core.backtest import engine
from friday.core.backtest.engine import CustomTrade, Day


def daily(start: str, values: list[str]) -> engine.Series:
    """One NAV per calendar day from ``start``."""
    first = date.fromisoformat(start)
    return [(first + timedelta(days=i), D(v)) for i, v in enumerate(values)]


def monthly(count: int, values: list[str] | str, year: int = 2020) -> engine.Series:
    """One NAV on the 1st of each month."""
    navs = values if isinstance(values, list) else [values] * count
    return [(date(year + m // 12, m % 12 + 1, 1), D(navs[m])) for m in range(count)]


def test_align_carries_navs_forward_and_starts_when_every_fund_has_one() -> None:
    aligned = engine.align(
        {1: daily("2020-01-01", ["10", "11", "12"]), 2: daily("2020-01-02", ["20", "21"])}
    )

    assert aligned.dates == [date(2020, 1, 1), date(2020, 1, 2), date(2020, 1, 3)]
    assert aligned.start == 1
    assert aligned.navs[1] == [D(10), D(11), D(12)]
    assert aligned.navs[2] == [None, D(20), D(21)]


def test_align_uses_the_last_nav_before_the_window() -> None:
    points = [(date(2019, 12, 31), D("50")), (date(2020, 1, 3), D("51"))]
    aligned = engine.align({1: points, 2: daily("2020-01-01", ["1", "1", "1"])}, date(2020, 1, 1))

    assert aligned.start == 0
    assert aligned.navs[1] == [D(50), D(50), D(51)]


def test_despike_replaces_bad_ticks_and_counts_them() -> None:
    cleaned, replaced = engine.despike(
        daily("2020-01-01", ["100", "101", "10", "10", "102", "103", "101"])
    )

    assert replaced == 2
    assert [nav for _, nav in cleaned] == [
        D(n) for n in ("100", "101", "101", "101", "102", "103", "101")
    ]


def test_despike_keeps_a_good_nav_next_to_two_bad_ones() -> None:
    # Friday compared with 2 neighbours each side, so 101 (next to two 10s) became 10.
    points = daily("2020-01-01", ["100", "101", "10", "10", "102", "103", "101", "100"])
    cleaned, _ = engine.despike(points)

    assert cleaned[1][1] == D(101)
    assert min(nav for _, nav in cleaned) > 90


def test_despike_ignores_neighbours_across_a_gap() -> None:
    # Seven years apart is growth, not a bad tick.
    old = [(date(2013, 5, 28 + i), D("10")) for i in range(3)]
    new = [(date(2026, 10, 12 + i), D("89")) for i in range(5)]

    assert engine.despike(old + new) == (old + new, 0)


def test_despike_leaves_real_moves_alone() -> None:
    points = daily("2020-01-01", ["100", "95", "88", "92", "97", "99"])  # a 12% fall is real
    assert engine.despike(points) == (points, 0)


def test_xirr_of_ten_percent_in_a_year() -> None:
    assert engine.xirr([(date(2021, 1, 1), -1000.0), (date(2022, 1, 1), 1100.0)]) == pytest.approx(
        0.10, abs=1e-6
    )
    assert engine.xirr([(date(2021, 1, 1), -1000.0)]) is None


def test_max_drawdown_is_the_largest_fall_from_a_peak() -> None:
    assert engine.max_drawdown([100, 120, 90, 130]) == pytest.approx(0.25)


def test_regular_doubles_when_the_fund_doubles() -> None:
    aligned = engine.align({1: [(date(2021, 1, 1), D(100)), (date(2022, 1, 1), D(200))]})

    run = engine.run_regular(aligned, [(1, D(100))], D(1000))
    m = engine.metrics(run.days)

    assert run.days[-1].value == D(2000)
    assert (m.total_invested, m.absolute_return_pct) == (D(1000), D(100))
    assert m.cagr_pct == pytest.approx(100)
    assert m.xirr_pct == pytest.approx(100)


def test_regular_splits_capital_by_weight() -> None:
    aligned = engine.align(
        {1: daily("2020-01-01", ["100", "110"]), 2: daily("2020-01-01", ["50", "50"])}
    )

    run = engine.run_regular(aligned, [(1, D(50)), (2, D(50))], D(1000))

    assert run.days[-1].value == D(1050)  # 500 grows 10%, 500 stays
    assert [outcome.units for outcome in run.funds] == [D(5), D(10)]


def test_yearly_rebalance_by_hand() -> None:
    a = [
        (date(2020, 1, 1), D(100)),
        (date(2020, 12, 31), D(200)),
        (date(2021, 1, 4), D(200)),
        (date(2021, 12, 31), D(200)),
    ]
    b = [
        (date(2020, 1, 1), D(50)),
        (date(2020, 12, 31), D(50)),
        (date(2021, 1, 4), D(50)),
        (date(2021, 12, 31), D(100)),
    ]
    aligned = engine.align({1: a, 2: b})
    weights = [(1, D(50)), (2, D(50))]

    # A doubles in 2020, B doubles in 2021. Rebalanced on 4 Jan 2021: 1500 → 750 + 750,
    # i.e. 3.75 units of A and 15 of B; at the end 3.75 × 200 + 15 × 100 = 2250.
    assert engine.run_regular(aligned, weights, D(1000), "yearly").days[-1].value == D(2250)
    # Held as bought: 5 × 200 + 10 × 100 = 2000.
    assert engine.run_regular(aligned, weights, D(1000)).days[-1].value == D(2000)


def test_sip_at_a_flat_nav_returns_nothing() -> None:
    run = engine.run_sip(engine.align({1: monthly(12, "100")}), [(1, D(100))], D(1000))
    m = engine.metrics(run.days)

    assert (m.total_invested, m.end_value, m.absolute_return_pct) == (D(12000), D(12000), D(0))
    assert m.xirr_pct == pytest.approx(0, abs=1e-6)


def test_sip_by_hand() -> None:
    # ₹1,000 at NAV 10 buys 100 units, at NAV 20 buys 50; 150 units at 20 = ₹3,000 for ₹2,000.
    run = engine.run_sip(engine.align({1: monthly(2, ["10", "20"])}), [(1, D(100))], D(1000))
    m = engine.metrics(run.days)

    assert run.funds[0].units == D(150)
    assert (m.end_value, m.total_invested, m.absolute_return_pct) == (D(3000), D(2000), D(50))
    assert [day.flow for day in run.days] == [D(1000), D(1000)]


def test_weekly_sip_invests_once_per_iso_week() -> None:
    points = daily("2026-10-01", ["10"] * 14)  # Thursday 1 Oct to Wednesday 14 Oct
    run = engine.run_sip(engine.align({1: points}), [(1, D(100))], D(500), "weekly")

    assert [day.date.isoformat() for day in run.days if day.flow] == [
        "2026-10-01",
        "2026-10-05",
        "2026-10-12",
    ]


def test_swp_runs_out_of_money() -> None:
    run = engine.run_swp(engine.align({1: monthly(7, "100")}), [(1, D(100))], D(1000), D(300))
    m = engine.metrics(run.days, depletion=run.depletion_date)

    assert m.total_withdrawn == D(1000)  # 300 + 300 + 300 + the last 100
    assert run.days[-1].value == D(0)
    assert run.depletion_date == date(2020, 5, 1)
    assert run.warnings == ["The money ran out on 2020-05-01."]


def test_swp_sells_each_fund_in_proportion() -> None:
    aligned = engine.align({1: monthly(2, "10"), 2: monthly(2, "20")})

    run = engine.run_swp(aligned, [(1, D(75)), (2, D(25))], D(1000), D(100))

    assert [outcome.end_value for outcome in run.funds] == [D("675"), D("225")]


NAMES = {1: "Flexi", 2: "Small"}


def test_custom_switch_nets_off_and_tracks_the_new_fund() -> None:
    aligned = engine.align(
        {1: daily("2020-01-01", ["100", "100", "100"]), 2: daily("2020-01-01", ["50", "50", "100"])}
    )
    trades = [
        CustomTrade(1, date(2020, 1, 1), "buy", amount=D(1000)),
        CustomTrade(
            2, date(2020, 1, 2), "buy", amount=D(1000)
        ),  # listed first, runs after the sell
        CustomTrade(1, date(2020, 1, 2), "sell", sell_all=True),
    ]

    run = engine.run_custom(aligned, trades, NAMES)

    assert run.days[-1].value == D(2000)  # 20 units of the fund that doubled
    assert [(t.side, t.instrument_id) for t in run.trades] == [("buy", 1), ("sell", 1), ("buy", 2)]
    assert [day.flow for day in run.days] == [D(1000), D(0), D(0)]  # the switch funds itself
    assert (run.days[-1].invested, run.days[-1].withdrawn) == (D(1000), D(0))
    flexi, small = run.funds
    assert (flexi.invested, flexi.proceeds, flexi.end_value) == (D(1000), D(1000), D(0))
    assert (small.invested, small.units) == (D(1000), D(20))


def test_custom_caps_an_oversell_and_says_so() -> None:
    aligned = engine.align({1: daily("2020-01-01", ["100", "100"])})
    trades = [
        CustomTrade(1, date(2020, 1, 1), "buy", units=D(5)),
        CustomTrade(1, date(2020, 1, 2), "sell", units=D(999)),
    ]

    run = engine.run_custom(aligned, trades, NAMES)

    assert run.funds[0].units == D(0)
    assert run.trades[-1].amount == D(500)
    assert run.warnings == [
        "A sell of Flexi on 2020-01-02 was more than the holding, so only the holding was sold."
    ]


def test_custom_trade_on_a_holiday_runs_on_the_next_nav_date() -> None:
    aligned = engine.align({1: [(date(2020, 1, 3), D(10)), (date(2020, 1, 6), D(11))]})

    run = engine.run_custom(
        aligned, [CustomTrade(1, date(2020, 1, 4), "buy", amount=D(110))], NAMES
    )

    assert run.trades[0].date == date(2020, 1, 6)
    assert run.trades[0].units == D(10)


def test_custom_trade_after_the_last_nav_is_skipped() -> None:
    aligned = engine.align({1: daily("2020-01-01", ["10", "10"])})
    trades = [
        CustomTrade(1, date(2020, 1, 1), "buy", amount=D(100)),
        CustomTrade(1, date(2021, 1, 1), "buy", amount=D(100)),
    ]

    run = engine.run_custom(aligned, trades, NAMES)

    assert len(run.trades) == 1
    assert "Skipped a buy of Flexi on 2021-01-01" in run.warnings[0]


def test_benchmark_gets_the_same_money_on_the_same_dates() -> None:
    model = engine.run_sip(engine.align({1: monthly(2, ["10", "10"])}), [(1, D(100))], D(1000))
    index_fund = monthly(2, ["10", "20"])

    bench = engine.replay_flows(index_fund, model.days)

    # 100 units, then 50 more at 20: 150 units at 20 = 3000 for the same 2000 put in.
    assert [(day.value, day.invested) for day in bench] == [(D(1000), D(1000)), (D(3000), D(2000))]
    assert engine.replay_flows(monthly(2, ["10", "20"], year=2021), model.days) is None


def test_benchmark_withdrawals_are_capped_at_its_holding() -> None:
    days = [
        Day(date(2020, 1, 1), D(1000), D(1000), D(0), D(1000)),
        Day(date(2020, 2, 1), D(0), D(1000), D(900), D(-900)),
    ]

    bench = engine.replay_flows([(date(2020, 1, 1), D(10)), (date(2020, 2, 1), D(5))], days)

    assert (bench[-1].value, bench[-1].withdrawn) == (D(0), D(500))


def test_growth_index_ignores_money_moving() -> None:
    days = [
        Day(date(2020, 1, 1), D(1000), D(1000), D(0), D(1000)),
        Day(date(2020, 1, 11), D(1600), D(1500), D(0), D(500)),  # 1100 before 500 came in
        Day(date(2020, 1, 21), D(1700), D(1500), D(0), D(0)),
    ]

    assert engine.growth_index(days) == pytest.approx([100, 110, 110 * 1700 / 1600])


def test_interval_return_is_modified_dietz_by_hand() -> None:
    days = [
        Day(date(2020, 1, 1), D(1000), D(1000), D(0), D(1000)),
        Day(date(2020, 1, 11), D(1600), D(1500), D(0), D(500)),
        Day(date(2020, 1, 21), D(1700), D(1500), D(0), D(0)),
    ]

    window = engine.interval(days, date(2020, 1, 1), date(2020, 1, 21))

    # Gain 1700 − 1000 − 500 = 200, over 1000 + 500 × (10 of 20 days left) = 1250 → 16%.
    assert window.return_pct == D(16)
    assert (window.invested, window.withdrawn) == (D(500), D(0))
    assert engine.interval(days, date(2020, 1, 21), None) is None  # one date isn't a window


def test_figures_round_half_up_and_drop_negative_zero() -> None:
    assert engine.figure(12.345) == D("12.35")
    assert str(engine.figure(-0.001)) == "0.00"
    assert engine.figure(float("nan")) is None
    assert engine.figure(None) is None
    assert engine.figure(1.6e27) is None


def test_no_common_nav_dates_is_an_error() -> None:
    aligned = engine.align({1: daily("2020-01-01", ["10"]), 2: []})
    with pytest.raises(engine.EngineError):
        engine.run_regular(aligned, [(1, D(50)), (2, D(50))], D(1000))
