"""The split search (D-077, D-078): the grid, agreement with the engine, and the ranking."""

import math
import random
from datetime import date, timedelta
from decimal import Decimal as D

import numpy as np
import pytest

from friday.core.backtest import engine, search


def wandering(seed: int, days: int, drift: float, swing: float) -> engine.Series:
    """A NAV that wanders day to day, weekdays only, like a fund."""
    rng, nav, points = random.Random(seed), 100.0, []
    day = date(2021, 1, 1)
    while len(points) < days:
        if day.weekday() < 5:
            nav *= 1 + drift + rng.gauss(0, swing)
            points.append((day, D(f"{nav:.4f}")))
        day += timedelta(days=1)
    return points


@pytest.fixture
def aligned() -> engine.Aligned:
    return engine.align(
        {
            1: wandering(1, 600, 0.0006, 0.012),
            2: wandering(2, 600, 0.0003, 0.006),
            3: wandering(3, 600, 0.0001, 0.001),
        }
    )


@pytest.mark.parametrize(
    ("funds", "step", "low", "high", "count"),
    [(3, 5, 0, 100, 231), (3, 5, 5, 100, 171), (5, 5, 0, 100, 10626), (2, 10, 20, 60, 3)],
)
def test_the_grid_has_every_split_once(funds, step, low, high, count) -> None:
    splits = search.grid(funds, step, low, high)

    assert len(splits) == len(set(splits)) == count == search.count_splits(funds, step, low, high)
    assert all(sum(split) == 100 and all(low <= w <= high for w in split) for split in splits)


def test_two_funds_in_steps_of_ten_by_hand() -> None:
    assert search.grid(2, 10, 20, 60) == [(40, 60), (50, 50), (60, 40)]


@pytest.mark.parametrize(
    "plan",
    [
        search.Plan("regular", 100000.0, "none"),
        search.Plan("regular", 100000.0, "quarterly"),
        search.Plan("sip", 10000.0, "monthly"),
    ],
)
def test_the_search_agrees_with_the_engine(aligned, plan) -> None:
    splits = [(60, 30, 10), (0, 0, 100), (35, 35, 30)]

    got = search.measure(aligned, [1, 2, 3], splits, plan, 6.5)

    for k, split in enumerate(splits):
        weights = [(fund, D(w)) for fund, w in zip([1, 2, 3], split, strict=True) if w]
        if plan.strategy == "sip":
            run = engine.run_sip(aligned, weights, D(10000), plan.period)
        else:
            run = engine.run_regular(aligned, weights, D(100000), plan.period)
        want = engine.metrics(run.days, D("6.5"))
        assert got.xirr_pct[k] == pytest.approx(want.xirr_pct, abs=1e-6)
        assert got.cagr_pct[k] == pytest.approx(want.cagr_pct, abs=1e-6)
        assert got.max_drawdown_pct[k] == pytest.approx(want.max_drawdown_pct, abs=1e-6)
        assert got.volatility_pct[k] == pytest.approx(want.volatility_pct, abs=1e-6)
        assert got.sharpe[k] == pytest.approx(want.sharpe, abs=1e-6)


def measures(xirr, drawdown, sharpe) -> search.Measures:
    nan = [math.nan] * len(xirr)
    return search.Measures(
        np.array(xirr), np.array(nan), np.array(drawdown), np.array(nan), np.array(sharpe)
    )


def test_ranking_for_each_goal_within_the_limits() -> None:
    m = measures(
        xirr=[18.0, 15.0, 12.0, 15.0, math.nan],
        drawdown=[40.0, 25.0, 10.0, 20.0, 5.0],
        sharpe=[0.9, 1.1, 0.8, 1.2, math.nan],
    )

    assert search.rank(m, "xirr", None, None, 3)[1] == [0, 3, 1]  # equal XIRR: less drawdown
    assert search.rank(m, "drawdown", None, None, 2)[1] == [4, 2]
    assert search.rank(m, "sharpe", None, None, 2)[1] == [3, 1]
    eligible, best = search.rank(m, "xirr", 30.0, 13.0, 10)
    assert eligible.tolist() == [False, True, False, True, False]
    assert best == [3, 1]
