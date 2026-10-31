"""Every split of a model's funds, measured together. Pure, no I/O.

Each split's value curve is the funds' own curves combined by weight, so thousands of splits
are worked out at once with numpy, in floats. The figures here only rank splits: the ones
shown are re-run with the exact engine by the service. The formulas follow
:func:`friday.core.backtest.engine.metrics` line by line, so a split comes out the same here
as there to the rounding.
"""

import math
from dataclasses import dataclass
from datetime import date

import numpy as np

from friday.core.backtest import engine
from friday.core.backtest.engine import Aligned, EngineError

MAX_FUNDS = 5
MAX_SPLITS = 50_000
CHUNK = 2_000
"""Splits measured at a time, to keep the value matrix small (2,000 × days × 8 bytes)."""

GOALS = ("xirr", "drawdown", "sharpe")


def _allowed(step: int, low: int, high: int) -> list[int]:
    return [weight for weight in range(0, 101, step) if low <= weight <= high]


def count_splits(funds: int, step: int, low: int, high: int) -> int:
    """How many splits :func:`grid` would make, without making them."""
    ways = {0: 1}
    for _ in range(funds):
        nxt: dict[int, int] = {}
        for total, count in ways.items():
            for weight in _allowed(step, low, high):
                if total + weight <= 100:
                    nxt[total + weight] = nxt.get(total + weight, 0) + count
        ways = nxt
    return ways.get(100, 0)


def grid(funds: int, step: int, low: int, high: int) -> list[tuple[int, ...]]:
    """Every split of ``funds`` whole-percent weights, multiples of ``step`` between ``low``
    and ``high``, adding up to 100; in order, first fund's weight first."""
    values = _allowed(step, low, high)
    splits: list[tuple[int, ...]] = []

    def walk(prefix: tuple[int, ...], left: int) -> None:
        if len(prefix) == funds - 1:
            if left in values:
                splits.append((*prefix, left))
            return
        for weight in values:
            if weight > left:
                break
            walk((*prefix, weight), left - weight)

    walk((), 100)
    return splits


@dataclass(frozen=True)
class Plan:
    """What every split does: a lump sum (rebalanced every ``period``, or never) or a SIP of
    ``amount`` every ``period``."""

    strategy: str  # regular | sip
    amount: float
    period: str


@dataclass
class Measures:
    """One value per split, in the order of the splits. ``nan`` where the engine has none."""

    xirr_pct: np.ndarray
    cagr_pct: np.ndarray
    max_drawdown_pct: np.ndarray
    volatility_pct: np.ndarray
    sharpe: np.ndarray


def _starts(dates: list[date], period: str) -> list[int]:
    """Indices where a new period starts (always 0), as the engine's ``period_key`` sees it."""
    keys = [engine.period_key(day, period) for day in dates]
    return [i for i in range(len(keys)) if i == 0 or keys[i] != keys[i - 1]]


def _values(prices: np.ndarray, weights: np.ndarray, plan: Plan, dates: list[date]):
    """Value of every split on every date (splits × dates), and the money put in each date."""
    flows = np.zeros(len(dates))
    if plan.strategy == "sip":
        buys = _starts(dates, plan.period)
        flows[buys] = plan.amount
        bought = np.zeros_like(prices)
        bought[buys] = 1.0 / prices[buys]
        held = np.cumsum(bought, axis=0) * prices  # each fund's worth of 1 a period
        return plan.amount * weights @ held.T, flows
    flows[0] = plan.amount
    if plan.period == "none":
        return plan.amount * weights @ (prices / prices[0]).T, flows
    values = np.empty((len(weights), len(dates)))
    base = np.full(len(weights), plan.amount)
    bounds = [*_starts(dates, plan.period), len(dates)]
    for b, e in zip(bounds, bounds[1:], strict=False):
        values[:, b:e] = base[:, None] * (weights @ (prices[b:e] / prices[b]).T)
        if e < len(dates):  # rebalanced at e: the same money, back to the weights
            base = base * (weights @ (prices[e] / prices[b]))
    return values, flows


def _xirr(flows: np.ndarray, dates: list[date], end_values: np.ndarray) -> np.ndarray:
    """The engine's XIRR for every split at once: the money in is the same for all of them,
    only the value at the end differs. Newton's method; the engine's own solver where it
    doesn't settle."""
    days = [i for i in range(len(dates)) if flows[i] != 0]
    t = np.array([(dates[i] - dates[days[0]]).days / 365 for i in days])
    cash = -flows[days]
    end = (dates[-1] - dates[days[0]]).days / 365
    rate = np.full(len(end_values), 0.1)
    with np.errstate(all="ignore"):
        for _ in range(100):
            grow = 1 + rate
            npv = (cash[None, :] * grow[:, None] ** -t).sum(1) + end_values * grow**-end
            slope = (-t * cash[None, :] * grow[:, None] ** (-t - 1)).sum(1) - (
                end * end_values * grow ** (-end - 1)
            )
            step = np.where(slope != 0, npv / slope, 0)
            nxt = np.maximum(rate - step, -0.9999)
            done = np.abs(nxt - rate) < 1e-9
            rate = nxt
            if done.all():
                break
    settled = np.isfinite(rate) & done
    for k in np.flatnonzero(~settled):
        flows_k = [(dates[i], float(-flows[i])) for i in days] + [(dates[-1], end_values[k])]
        found = engine.xirr(flows_k)
        rate[k] = found if found is not None else np.nan
    return rate * 100


def measure(
    aligned: Aligned, funds: list[int], splits: list[tuple[int, ...]], plan: Plan, rf_pct: float
) -> Measures:
    """XIRR, CAGR, max drawdown, volatility and Sharpe of every split, as the engine works
    them out, from the first date every fund has a NAV."""
    if aligned.start >= len(aligned.dates) - 1:
        raise EngineError("the funds have no NAVs in common for these dates")
    dates = aligned.dates[aligned.start :]
    prices = np.array(
        [
            [float(aligned.navs[fund][i]) for fund in funds]
            for i in range(aligned.start, len(aligned.dates))
        ]
    )
    years = (dates[-1] - dates[0]).days / 365
    parts: list[list[np.ndarray]] = [[], [], [], [], []]
    for first in range(0, len(splits), CHUNK):
        weights = np.array(splits[first : first + CHUNK], dtype=float) / 100
        values, flows = _values(prices, weights, plan, dates)
        with np.errstate(all="ignore"):
            returns = (values[:, 1:] - flows[1:]) / values[:, :-1] - 1
            index = 100 * np.cumprod(np.hstack([np.ones((len(weights), 1)), 1 + returns]), 1)
            drawdown = (1 - index / np.maximum.accumulate(index, axis=1)).max(1)
            mean = returns.mean(1)
            volatility = returns.std(1, ddof=1) * math.sqrt(engine.TRADING_DAYS)
            yearly = (1 + mean) ** engine.TRADING_DAYS - 1
            sharpe = np.where(volatility > 0, (yearly - rf_pct / 100) / volatility, np.nan)
            cagr = (index[:, -1] / index[:, 0]) ** (1 / years) - 1 if years > 0 else None
        parts[0].append(_xirr(flows, dates, values[:, -1]))
        parts[1].append(cagr * 100 if cagr is not None else np.full(len(weights), np.nan))
        parts[2].append(drawdown * 100)
        parts[3].append(volatility * 100)
        parts[4].append(sharpe)
    return Measures(*(np.concatenate(part) for part in parts))


def rank(
    m: Measures,
    goal: str,
    max_drawdown_pct: float | None,
    min_xirr_pct: float | None,
    top: int,
) -> tuple[np.ndarray, list[int]]:
    """Which splits are within the limits, and the best ``top`` of those for ``goal``
    (ties go to the smaller drawdown, or for the drawdown goal the higher XIRR)."""
    eligible = np.ones(len(m.xirr_pct), dtype=bool)
    if max_drawdown_pct is not None:
        eligible &= m.max_drawdown_pct <= max_drawdown_pct
    if min_xirr_pct is not None:
        eligible &= np.nan_to_num(m.xirr_pct, nan=-np.inf) >= min_xirr_pct
    xirr = np.nan_to_num(m.xirr_pct, nan=-np.inf)
    if goal == "xirr":
        keys = (m.max_drawdown_pct, -xirr)
    elif goal == "drawdown":
        keys = (-xirr, m.max_drawdown_pct)
    else:
        keys = (m.max_drawdown_pct, -np.nan_to_num(m.sharpe, nan=-np.inf))
    order = np.lexsort(keys)  # the last key sorts first
    best = [int(k) for k in order if eligible[k]][:top]
    return eligible, best
