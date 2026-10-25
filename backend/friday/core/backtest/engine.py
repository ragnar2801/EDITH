"""Backtest engine (D-048), ported from Friday's TypeScript engine. Pure functions, no I/O.

Money and units are exact ``Decimal``s, like a ledger: a ₹10,000 SIP instalment is exactly
₹10,000 invested. Ratios (XIRR, CAGR, volatility, Sharpe, Sortino, drawdown) are floats,
rounded to 2 places when reported.

Every strategy produces one row per date (:class:`Day`): the portfolio value, the money put
in and taken out so far, and the money that moved that day. Metrics, the time-weighted
index, the benchmark and interval figures are all computed from those rows, the same way
for every strategy.
"""

import math
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

ZERO = Decimal(0)
HUNDRED = Decimal(100)
CENT = Decimal("0.01")
SPIKE_HIGH = Decimal("1.8")
SPIKE_LOW = Decimal("0.55")
TRADING_DAYS = 252

Series = list[tuple[date, Decimal]]
FREQUENCIES = ("weekly", "monthly", "quarterly")
REBALANCE = ("none", "monthly", "quarterly", "yearly")


class EngineError(ValueError):
    """The backtest can't run with this data or these inputs."""


# --- Data preparation ------------------------------------------------------------------


SPIKE_WINDOW = 5
"""NAVs on each side a NAV is compared with. Friday used 2, which let two bad ticks in a row
outvote a good NAV next to them."""
SPIKE_DAYS = 15
"""Only NAVs this close in time are compared, so a gap in the history isn't a spike."""


def despike(points: Series) -> tuple[Series, int]:
    """Replace NAVs more than 1.8× or under 0.55× the median of the NAVs around them (up to
    5 each side, within 15 days): bad ticks rather than real moves, which never go that far
    in a day. Returns the cleaned series and how many NAVs were replaced."""
    n = len(points)
    cleaned, replaced = [nav for _, nav in points], 0
    for i, (day, nav) in enumerate(points):
        lo, hi = max(0, i - SPIKE_WINDOW), min(n, i + SPIKE_WINDOW + 1)
        window = sorted(
            points[j][1]
            for j in range(lo, hi)
            if j != i and abs((points[j][0] - day).days) <= SPIKE_DAYS
        )
        if len(window) < 4:
            continue
        median = window[len(window) // 2]
        if nav > median * SPIKE_HIGH or nav < median * SPIKE_LOW:
            cleaned[i] = median
            replaced += 1
    if not replaced:
        return points, 0
    return [(day, cleaned[i]) for i, (day, _) in enumerate(points)], replaced


@dataclass
class Aligned:
    """NAVs of several funds on one date axis, each carried forward over days it has none."""

    dates: list[date]
    navs: dict[int, list[Decimal | None]]
    start: int
    """First index where every fund has a NAV; ``len(dates)`` if there is none."""


def align(series: dict[int, Series], start: date | None = None, end: date | None = None) -> Aligned:
    dates = sorted(
        {
            day
            for points in series.values()
            for day, _ in points
            if (start is None or day >= start) and (end is None or day <= end)
        }
    )
    navs: dict[int, list[Decimal | None]] = {}
    firsts = []
    for fund, points in series.items():
        by_date = dict(points)
        before = [nav for day, nav in points if dates and day < dates[0]]
        last = before[-1] if before else None
        first = 0 if last is not None else None
        column: list[Decimal | None] = []
        for i, day in enumerate(dates):
            if day in by_date:
                last = by_date[day]
                if first is None:
                    first = i
            column.append(last)
        navs[fund] = column
        firsts.append(len(dates) if first is None else first)
    return Aligned(dates, navs, max(firsts) if firsts else len(dates))


def period_key(day: date, frequency: str) -> tuple:
    """Which period a date falls in, to find the first NAV date of each period."""
    if frequency == "weekly":
        return day.isocalendar()[:2]  # ISO weeks start on Monday
    if frequency == "monthly":
        return (day.year, day.month)
    if frequency == "quarterly":
        return (day.year, (day.month - 1) // 3)
    if frequency == "yearly":
        return (day.year,)
    return ()


# --- One row per date ------------------------------------------------------------------


@dataclass
class Day:
    date: date
    value: Decimal
    invested: Decimal
    """Money put in so far."""
    withdrawn: Decimal
    """Money taken out so far (SWP withdrawals, custom sells)."""
    flow: Decimal
    """Money that moved today: in (+) or out (−)."""


@dataclass
class Trade:
    date: date
    instrument_id: int
    side: str  # buy | sell
    units: Decimal
    nav: Decimal
    amount: Decimal


@dataclass
class FundOutcome:
    instrument_id: int
    units: Decimal
    end_value: Decimal
    weight: Decimal | None = None
    invested: Decimal | None = None
    proceeds: Decimal | None = None


@dataclass
class Run:
    days: list[Day]
    funds: list[FundOutcome]
    trades: list[Trade] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    depletion_date: date | None = None


def _value(units: dict[int, Decimal], aligned: Aligned, i: int) -> Decimal:
    total = ZERO
    for fund, held in units.items():
        nav = aligned.navs[fund][i]
        if held and nav is not None:
            total += held * nav
    return total


def _split(amount: Decimal, weights: list[tuple[int, Decimal]], aligned: Aligned, i: int):
    """Units bought when ``amount`` is spread over the funds by weight (percent)."""
    return {fund: amount * weight / HUNDRED / aligned.navs[fund][i] for fund, weight in weights}


def _outcomes(units, aligned: Aligned, weights) -> list[FundOutcome]:
    last = len(aligned.dates) - 1
    return [
        FundOutcome(
            instrument_id=fund,
            units=units[fund],
            end_value=units[fund] * (aligned.navs[fund][last] or ZERO),
            weight=weight,
        )
        for fund, weight in weights
    ]


def _require_start(aligned: Aligned) -> None:
    if aligned.start >= len(aligned.dates):
        raise EngineError("the funds have no NAVs in common for these dates")


# --- Strategies ------------------------------------------------------------------------


def run_regular(aligned: Aligned, weights, capital: Decimal, rebalance: str = "none") -> Run:
    """Lump sum on the first date every fund has a NAV, optionally rebalanced to the weights
    at the start of each period."""
    _require_start(aligned)
    s = aligned.start
    units = _split(capital, weights, aligned, s)
    key = period_key(aligned.dates[s], rebalance)
    days = []
    for i in range(s, len(aligned.dates)):
        if rebalance != "none" and i > s and period_key(aligned.dates[i], rebalance) != key:
            key = period_key(aligned.dates[i], rebalance)
            units = _split(_value(units, aligned, i), weights, aligned, i)
        flow = capital if i == s else ZERO
        days.append(Day(aligned.dates[i], _value(units, aligned, i), capital, ZERO, flow))
    return Run(days, _outcomes(units, aligned, weights))


def run_sip(aligned: Aligned, weights, amount: Decimal, frequency: str = "monthly") -> Run:
    """``amount`` invested on the first NAV date of every period, split by weight."""
    _require_start(aligned)
    units = {fund: ZERO for fund, _ in weights}
    invested, key, days = ZERO, None, []
    for i in range(aligned.start, len(aligned.dates)):
        flow = ZERO
        this = period_key(aligned.dates[i], frequency)
        if this != key:
            key = this
            for fund, bought in _split(amount, weights, aligned, i).items():
                units[fund] += bought
            invested += amount
            flow = amount
        days.append(Day(aligned.dates[i], _value(units, aligned, i), invested, ZERO, flow))
    return Run(days, _outcomes(units, aligned, weights))


def run_swp(
    aligned: Aligned, weights, corpus: Decimal, amount: Decimal, frequency: str = "monthly"
) -> Run:
    """Invest ``corpus``, then withdraw ``amount`` at the start of every later period, selling
    each fund in proportion to its value. Stops when the money runs out."""
    _require_start(aligned)
    s = aligned.start
    units = _split(corpus, weights, aligned, s)
    key = period_key(aligned.dates[s], frequency)  # nothing is withdrawn on day one
    withdrawn, depleted, days = ZERO, None, []
    for i in range(s, len(aligned.dates)):
        flow = corpus if i == s else ZERO
        this = period_key(aligned.dates[i], frequency)
        if i > s and this != key:
            key = this
            if depleted is None:
                value = _value(units, aligned, i)
                take = min(amount, value)
                if take > 0:
                    for fund in units:  # each fund sells its share of the withdrawal
                        units[fund] -= take * units[fund] / value
                    withdrawn += take
                    flow -= take
                if take < amount:
                    depleted = aligned.dates[i]
        value = max(ZERO, _value(units, aligned, i))
        days.append(Day(aligned.dates[i], value, corpus, withdrawn, flow))
    run = Run(days, _outcomes(units, aligned, weights), depletion_date=depleted)
    if depleted:
        run.warnings.append(f"The money ran out on {depleted.isoformat()}.")
    return run


@dataclass(frozen=True)
class CustomTrade:
    instrument_id: int
    date: date
    side: str  # buy | sell
    amount: Decimal | None = None
    units: Decimal | None = None
    sell_all: bool = False


def run_custom(aligned: Aligned, trades: list[CustomTrade], names: dict[int, str]) -> Run:
    """Replay my own buys and sells. Each executes on the first NAV date on or after its
    date; on the same day, sells go before buys so a switch funds itself: money put in and
    taken out count only what's left after netting the day's trades."""
    warnings: list[str] = []
    resolved: list[tuple[int, int, CustomTrade]] = []
    for order, trade in enumerate(trades):
        column = aligned.navs.get(trade.instrument_id)
        name = names.get(trade.instrument_id, f"#{trade.instrument_id}")
        at = next(
            (
                i
                for i, day in enumerate(aligned.dates)
                if day >= trade.date and column and column[i] is not None
            ),
            None,
        )
        if at is None:
            warnings.append(
                f"Skipped a {trade.side} of {name} on {trade.date.isoformat()}: no NAV then."
            )
            continue
        resolved.append((at, order, trade))
    if not resolved:
        raise EngineError("none of the trades could be placed on a NAV date")
    resolved.sort(key=lambda item: (item[0], item[2].side != "sell", item[1]))

    funds = list(dict.fromkeys(trade.instrument_id for _, _, trade in resolved))
    units = dict.fromkeys(funds, ZERO)
    bought = dict.fromkeys(funds, ZERO)
    sold = dict.fromkeys(funds, ZERO)
    by_day: dict[int, list[CustomTrade]] = {}
    for at, _, trade in resolved:
        by_day.setdefault(at, []).append(trade)

    executed, days = [], []
    invested = withdrawn = ZERO
    for i in range(resolved[0][0], len(aligned.dates)):
        flow = ZERO
        for trade in by_day.get(i, []):
            fund, nav, day = (
                trade.instrument_id,
                aligned.navs[trade.instrument_id][i],
                aligned.dates[i],
            )
            if trade.side == "buy":
                if trade.amount is not None:
                    count, money = trade.amount / nav, trade.amount
                else:
                    count, money = trade.units, trade.units * nav
                units[fund] += count
                bought[fund] += money
                flow += money
            else:
                held = units[fund]
                if trade.sell_all:
                    count, money = held, held * nav
                elif trade.amount is not None:
                    count, money = trade.amount / nav, trade.amount
                else:
                    count, money = trade.units, trade.units * nav
                if count > held:
                    warnings.append(
                        f"A sell of {names.get(fund, f'#{fund}')} on {day.isoformat()} was more "
                        "than the holding, so only the holding was sold."
                    )
                    count, money = held, held * nav
                if count <= 0:
                    continue
                units[fund] -= count
                sold[fund] += money
                flow -= money
            executed.append(Trade(day, fund, trade.side, count, nav, money))
        # A switch (sell and buy on one day) nets off: only the difference comes in or goes out.
        if flow > 0:
            invested += flow
        else:
            withdrawn -= flow
        days.append(Day(aligned.dates[i], _value(units, aligned, i), invested, withdrawn, flow))

    last = len(aligned.dates) - 1
    outcomes = [
        FundOutcome(
            instrument_id=fund,
            units=units[fund],
            end_value=units[fund] * (aligned.navs[fund][last] or ZERO),
            invested=bought[fund],
            proceeds=sold[fund],
        )
        for fund in funds
    ]
    return Run(days, outcomes, executed, warnings)


def replay_flows(series: Series, days: list[Day]) -> list[Day] | None:
    """The same money moving on the same dates, in one fund instead (the benchmark, D-048).
    Withdrawals are capped at what the fund holds. ``None`` if the fund has no NAV on the
    first date."""
    points = sorted(series)
    units, invested, withdrawn, out = ZERO, ZERO, ZERO, []
    j, nav = 0, None
    for day in days:
        while j < len(points) and points[j][0] <= day.date:
            nav = points[j][1]  # the latest NAV on or before this date
            j += 1
        if nav is None:
            return None
        flow = ZERO
        if day.flow > 0:
            units += day.flow / nav
            invested += day.flow
            flow = day.flow
        elif day.flow < 0:
            take = min(-day.flow, units * nav)
            units -= take / nav
            withdrawn += take
            flow = -take
        out.append(Day(day.date, units * nav, invested, withdrawn, flow))
    return out


# --- Metrics ---------------------------------------------------------------------------


def growth_index(days: list[Day]) -> list[float]:
    """Time-weighted growth of 100, with money in and out taken out of each day's return."""
    index, level = [], 100.0
    for i, day in enumerate(days):
        if i > 0:
            previous = float(days[i - 1].value)
            if previous > 0:
                level *= (float(day.value) - float(day.flow)) / previous
        index.append(level)
    return index


def xirr(flows: list[tuple[date, float]]) -> float | None:
    """Annual money-weighted return of dated cash flows (out < 0, in > 0)."""
    if len(flows) < 2 or not any(a < 0 for _, a in flows) or not any(a > 0 for _, a in flows):
        return None
    t0 = flows[0][0]
    times = [(day - t0).days / 365 for day, _ in flows]

    def npv(rate: float) -> float:
        return sum(a / (1 + rate) ** t for (_, a), t in zip(flows, times, strict=True))

    def slope(rate: float) -> float:
        return sum(-t * a / (1 + rate) ** (t + 1) for (_, a), t in zip(flows, times, strict=True))

    rate = 0.1
    for _ in range(100):
        try:
            value, d = npv(rate), slope(rate)
        except OverflowError, ZeroDivisionError:
            break
        if d == 0 or not math.isfinite(value) or not math.isfinite(d):
            break
        nxt = max(rate - value / d, -0.9999)
        if abs(nxt - rate) < 1e-9:
            return nxt
        rate = nxt

    lo, hi = -0.9999, 10.0
    f_lo, f_hi = npv(lo), npv(hi)
    if f_lo * f_hi > 0:
        return None
    for _ in range(300):
        mid = (lo + hi) / 2
        f_mid = npv(mid)
        if abs(f_mid) < 1e-7:
            return mid
        if f_lo * f_mid < 0:
            hi = mid
        else:
            lo, f_lo = mid, f_mid
    return (lo + hi) / 2


def max_drawdown(levels: Iterable[float]) -> float:
    """Largest fall from a peak, as a fraction (0.25 = 25%)."""
    peak, worst = -math.inf, 0.0
    for level in levels:
        peak = max(peak, level)
        if peak > 0:
            worst = max(worst, (peak - level) / peak)
    return worst


@dataclass
class Metrics:
    start_date: date
    end_date: date
    years: float
    start_value: Decimal
    end_value: Decimal
    total_invested: Decimal
    total_withdrawn: Decimal
    absolute_return_pct: Decimal | None
    cagr_pct: float | None
    xirr_pct: float | None
    max_drawdown_pct: float
    volatility_pct: float
    sharpe: float | None
    sortino: float | None
    depletion_date: date | None = None


def metrics(days: list[Day], risk_free_pct: Decimal = ZERO, depletion: date | None = None):
    first, last = days[0], days[-1]
    years = (last.date - first.date).days / 365
    invested = sum((day.flow for day in days if day.flow > 0), ZERO)
    withdrawn = -sum((day.flow for day in days if day.flow < 0), ZERO)
    absolute = ((last.value + withdrawn - invested) / invested * HUNDRED) if invested > 0 else None

    index = growth_index(days)
    cagr = None
    if years > 0 and index[-1] > 0:
        cagr = ((index[-1] / index[0]) ** (1 / years) - 1) * 100

    cash = [(day.date, -float(day.flow)) for day in days if day.flow != 0]
    cash.append((last.date, float(last.value)))
    rate = xirr(cash)

    returns = [index[i] / index[i - 1] - 1 for i in range(1, len(index)) if index[i - 1] > 0]
    mean = sum(returns) / len(returns) if returns else 0.0
    spread = (
        math.sqrt(sum((r - mean) ** 2 for r in returns) / (len(returns) - 1))
        if len(returns) > 1
        else 0.0
    )
    try:
        yearly_return = (1 + mean) ** TRADING_DAYS - 1
    except OverflowError:  # only with absurd data; the ratios then mean nothing
        yearly_return = math.inf
    volatility = spread * math.sqrt(TRADING_DAYS)
    downside = (
        math.sqrt(sum(r * r for r in returns if r < 0) / len(returns)) * math.sqrt(TRADING_DAYS)
        if returns
        else 0.0
    )
    rf = float(risk_free_pct) / 100
    return Metrics(
        start_date=first.date,
        end_date=last.date,
        years=years,
        start_value=first.value,
        end_value=last.value,
        total_invested=invested,
        total_withdrawn=withdrawn,
        absolute_return_pct=absolute,
        cagr_pct=cagr,
        xirr_pct=rate * 100 if rate is not None else None,
        max_drawdown_pct=max_drawdown(index) * 100,
        volatility_pct=volatility * 100,
        sharpe=(yearly_return - rf) / volatility if volatility > 0 else None,
        sortino=(yearly_return - rf) / downside if downside > 0 else None,
        depletion_date=depletion,
    )


@dataclass
class Interval:
    start_date: date
    end_date: date
    start_value: Decimal
    end_value: Decimal
    return_pct: Decimal | None
    """Money-weighted (Modified Dietz): money added or taken out isn't counted as gain."""
    max_drawdown_pct: float
    invested: Decimal
    withdrawn: Decimal


def interval(days: list[Day], start: date | None, end: date | None) -> Interval | None:
    """Figures for a window of a run: a slice of it, not a re-run (D-049)."""
    window = [
        day
        for day in days
        if (start is None or day.date >= start) and (end is None or day.date <= end)
    ]
    if len(window) < 2:
        return None
    first, last = window[0], window[-1]
    span = (last.date - first.date).days
    net, weighted = ZERO, ZERO
    for day in window[1:]:
        if day.flow:
            net += day.flow
            share = Decimal(span - (day.date - first.date).days) / span if span else ZERO
            weighted += share * day.flow
    base = first.value + weighted
    gain = last.value - first.value - net
    index = growth_index(window)
    return Interval(
        start_date=first.date,
        end_date=last.date,
        start_value=first.value,
        end_value=last.value,
        return_pct=gain / base * HUNDRED if base > 0 else None,
        max_drawdown_pct=max_drawdown(index) * 100,
        invested=last.invested - first.invested,
        withdrawn=last.withdrawn - first.withdrawn,
    )


def money(value: Decimal) -> Decimal:
    return value.quantize(CENT, ROUND_HALF_UP)


def figure(value: float | Decimal | None, places: int = 2) -> Decimal | None:
    """A ratio for reporting: rounded half up, and never ``-0.00``."""
    if value is None or (isinstance(value, float) and not math.isfinite(value)):
        return None
    if abs(value) >= 10**12:  # a ratio this size comes from broken data, not markets
        return None
    rounded = Decimal(str(value)).quantize(Decimal(1).scaleb(-places), ROUND_HALF_UP)
    return rounded if rounded != 0 else abs(rounded)
