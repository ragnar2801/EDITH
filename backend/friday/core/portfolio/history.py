"""Value over time: pure arithmetic over a fund's dated moves and its NAVs, no
database.

A **move** is one change to a holding on one date: a buy (units and cost up, money in) or
a sale (units and cost down, proceeds out). Walking the moves along a list of dates gives
each date's value, the cost of the units still held and the money that went in or out
since the date before. The gain between two dates is the change in value less the money
put in meanwhile; the return over them is time-weighted, so it doesn't depend on when the
money went in.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from friday.core.portfolio.returns import CENT, HUNDRED, ZERO, Flow, Returns, money, returns

MAX_POINTS = 500
"""Points drawn at most; longer histories keep the last date of each week, then of each
month. Gains and returns are always worked out on every date."""


@dataclass(frozen=True)
class Move:
    date: date
    units: Decimal
    """Units bought (above 0) or sold (below 0)."""
    cost: Decimal
    """Change in what the units still held cost: a buy's amount, minus a sale's cost."""
    flow: Decimal
    """Money in (a buy's amount) or out (a sale's proceeds, below 0)."""
    nav: Decimal
    """The trade's NAV: the price until the fund has a stored NAV on or before a date."""


@dataclass(frozen=True)
class Point:
    date: date
    value: Decimal
    """Each fund's value is rounded to the paisa, as in the totals, so the last point is
    the value Portfolio shows."""
    cost: Decimal
    """What the units still held cost, each fund's rounded to the paisa."""
    flow: Decimal
    """Money in less money out since the point before (for the first point, ever)."""


@dataclass(frozen=True)
class Change:
    start: date
    """The date the change is measured from (its value is the base)."""
    end: date
    gain: Decimal
    """Value at ``end`` − value at ``start`` − money put in between."""
    return_pct: Decimal | None
    """Time-weighted return between the two dates, in percent; ``None`` when nothing was
    held at the start of any step."""


def daily(
    moves: Iterable[Move], series: list[tuple[date, Decimal]], dates: list[date]
) -> list[Point]:
    """One fund's value, cost and money flow on each of ``dates`` (sorted). Each date is
    priced at the latest stored NAV on or before it, else at the latest trade's NAV."""
    moves = sorted(moves, key=lambda move: move.date)
    units = cost = ZERO
    stored = traded = None
    i = j = 0
    points = []
    for day in dates:
        flow = ZERO
        while i < len(moves) and moves[i].date <= day:
            move = moves[i]
            units += move.units
            cost += move.cost
            flow += move.flow
            traded = move.nav
            i += 1
        while j < len(series) and series[j][0] <= day:
            stored = series[j][1]
            j += 1
        price = stored if stored is not None else traded
        value = money(units * price) if price is not None else ZERO
        points.append(Point(day, value, money(cost), flow))
    return points


def combine(lines: list[list[Point]]) -> list[Point]:
    """Point-by-point sums of several funds' points on the same dates."""
    if not lines:
        return []
    return [
        Point(
            column[0].date,
            sum((p.value for p in column), ZERO),
            sum((p.cost for p in column), ZERO),
            sum((p.flow for p in column), ZERO),
        )
        for column in zip(*lines, strict=True)
    ]


def mirror(series: list[tuple[date, Decimal]], flows: list[Flow]) -> list[Move] | None:
    """The same money on the same dates in one other fund (the benchmark), each
    flow at that fund's NAV on or before its date. A sale takes out the same rupees,
    capped at what the other fund holds by then. ``None`` when the fund has no NAV on or
    before the first flow."""
    points = sorted(series)
    moves: list[Move] = []
    units, j, nav = ZERO, 0, None
    for flow in sorted(flows, key=lambda f: f.date):
        while j < len(points) and points[j][0] <= flow.date:
            nav = points[j][1]
            j += 1
        if nav is None:
            return None
        if flow.amount > 0:
            bought = flow.amount / nav
            units += bought
            moves.append(Move(flow.date, bought, flow.amount, flow.amount, nav))
        elif flow.amount < 0:
            if -flow.amount >= units * nav:
                out, sold = money(units * nav), units  # everything it holds
            else:
                out, sold = -flow.amount, -flow.amount / nav
            units -= sold
            if out:
                moves.append(Move(flow.date, -sold, ZERO, -out, nav))
    return moves


def replay(series: list[tuple[date, Decimal]], flows: list[Flow], on: date) -> Returns | None:
    """Returns of the same money in the benchmark (:func:`mirror`), valued on ``on``."""
    moves = mirror(series, flows)
    if moves is None:
        return None
    [end] = daily(moves, series, [on])
    return returns([Flow(move.date, move.flow) for move in moves], end.value, on)


def change(points: list[Point], start: date | None = None) -> Change | None:
    """Gain and time-weighted return from the last point on or before ``start`` (or from
    nothing, before the first point) to the last point. ``None`` without two points to
    compare."""
    if not points:
        return None
    base = -1
    if start is not None:
        for i, point in enumerate(points):
            if point.date > start:
                break
            base = i
    if base == len(points) - 1:
        return None
    before = points[base].value if base >= 0 else ZERO
    after = points[base + 1 :]
    gain = points[-1].value - before - sum((p.flow for p in after), ZERO)
    growth, steps, previous = Decimal(1), 0, before
    for point in after:
        if previous > 0:
            growth *= (point.value - point.flow) / previous
            steps += 1
        previous = point.value
    rate = ((growth - 1) * HUNDRED).quantize(CENT) if steps else None
    since = points[base].date if base >= 0 else points[0].date
    return Change(since, points[-1].date, money(gain), rate)


def thin(points: list[Point], limit: int = MAX_POINTS) -> list[Point]:
    """At most about ``limit`` points to draw: the last of each week, then of each month,
    always with the first and the last."""
    for period in (_week, _month):
        if len(points) <= limit:
            break
        kept = [
            point
            for point, after in zip(points, [*points[1:], None], strict=True)
            if after is None or period(after.date) != period(point.date)
        ]
        points = [points[0], *kept] if kept[0] is not points[0] else kept
    return points


def _week(day: date) -> tuple[int, int]:
    return day.isocalendar()[:2]


def _month(day: date) -> tuple[int, int]:
    return day.year, day.month
