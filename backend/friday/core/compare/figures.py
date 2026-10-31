"""Figures that put funds side by side. Pure functions, no I/O.

Funds only compare fairly over the same dates, so most figures use one window: from the
youngest fund's first NAV to the last NAV every fund has. Trailing and calendar-year returns
cover the same dates for every fund by construction, so they use each fund's whole history.
Ratios are floats, rounded with ``engine.figure`` when reported.
"""

import math
import statistics
from bisect import bisect_right
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from friday.core.backtest import engine
from friday.core.backtest.engine import Day, Series
from friday.core.navs.service import years_before

CAPITAL = Decimal(10_000)
"""The lump sum each fund's growth starts from."""
SIP_AMOUNT = Decimal(10_000)
"""The monthly SIP each fund gets."""
TRAILING_YEARS = (1, 3, 5, 10)
CALENDAR_YEARS = 10
"""Calendar years shown, the latest (year to date) included."""
MIN_WEEKS = 8
"""Weekly returns needed for a correlation."""
MIN_MONTHS = 6
"""Monthly returns needed for capture ratios."""
CHART_POINTS = 600
"""Above this many dates, curves keep one point a week: they are for drawing only."""


class History:
    """A fund's NAVs, oldest first, with lookups by date."""

    def __init__(self, points: Series) -> None:
        self.points = points
        self.dates = [day for day, _ in points]

    def __bool__(self) -> bool:
        return bool(self.points)

    @property
    def first(self) -> date:
        return self.dates[0]

    @property
    def last(self) -> date:
        return self.dates[-1]

    def at(self, day: date) -> Decimal | None:
        """The latest NAV on or before ``day``."""
        i = bisect_right(self.dates, day)
        return self.points[i - 1][1] if i else None


# --- The window ------------------------------------------------------------------------


@dataclass
class Window:
    start: date
    end: date
    members: list[int]
    """Funds with a NAV on or before ``start``: the ones the window's figures cover."""
    limited_by: int | None
    """The youngest member, when leaving it out would start the window earlier."""
    earliest_start: date | None
    """Where the window would start without ``limited_by``."""


def window(
    histories: dict[int, History], start: date | None = None, end: date | None = None
) -> Window | None:
    """The dates every fund has, or with ``start`` the funds that go back that far.
    ``None`` when no fund qualifies or the funds share no dates."""
    with_navs = {key: history for key, history in histories.items() if history}
    if start is None:
        members = list(with_navs)
    else:
        members = [key for key, history in with_navs.items() if history.first <= start]
    if not members:
        return None
    youngest = max(members, key=lambda key: with_navs[key].first)
    begin = start or with_navs[youngest].first
    finish = min(with_navs[key].last for key in members)
    if end is not None:
        finish = min(finish, end)
    if finish <= begin:
        return None
    limited_by, earliest = None, None
    others = [with_navs[key].first for key in members if key != youngest]
    if others and with_navs[youngest].first >= begin and max(others) < begin:
        limited_by, earliest = youngest, max(others)
    return Window(begin, finish, members, limited_by, earliest)


# --- One fund over the window ----------------------------------------------------------


@dataclass
class Rolling:
    years: int
    periods: int
    median_pct: float
    worst_pct: float
    best_pct: float
    beat_benchmark_pct: float | None
    """Share of periods the fund did better than the benchmark over the same dates."""
    curve: list[tuple[date, float]]


@dataclass
class Sip:
    invested: Decimal
    value: Decimal
    xirr_pct: float | None


@dataclass
class Recovery:
    days: int
    """From the peak before the largest fall until the fund was back at it, or until the
    window's end if it isn't yet."""
    recovered: bool


@dataclass
class WindowFigures:
    cagr_pct: float | None
    return_pct: float | None
    volatility_pct: float
    max_drawdown_pct: float
    recovery: Recovery | None
    calmar: float | None
    """CAGR ÷ largest fall."""
    upside_capture_pct: float | None
    downside_capture_pct: float | None
    rolling: Rolling | None
    sip: Sip
    growth: list[tuple[date, Decimal]]
    """What ``CAPITAL`` at the start grew to."""
    drawdown: list[tuple[date, float]]
    """Percent below the highest value so far (0 or negative)."""


def _days(dates: list[date], navs: list[Decimal]) -> list[Day]:
    """``CAPITAL`` bought on the first date and held."""
    return [
        Day(day, CAPITAL * nav / navs[0], CAPITAL, Decimal(0), CAPITAL if i == 0 else Decimal(0))
        for i, (day, nav) in enumerate(zip(dates, navs, strict=True))
    ]


def recovery(dates: list[date], levels: list[float]) -> Recovery | None:
    """How long the largest fall took to win back. ``None`` if the fund never fell."""
    peak_i, worst, worst_peak, worst_trough = 0, 0.0, 0, 0
    for i, level in enumerate(levels):
        if level >= levels[peak_i]:
            peak_i = i
        elif (fall := 1 - level / levels[peak_i]) > worst:
            worst, worst_peak, worst_trough = fall, peak_i, i
    if worst == 0:
        return None
    for i in range(worst_trough + 1, len(levels)):
        if levels[i] >= levels[worst_peak]:
            return Recovery((dates[i] - dates[worst_peak]).days, True)
    return Recovery((dates[-1] - dates[worst_peak]).days, False)


def drawdowns(levels: list[float]) -> list[float]:
    peak, out = -math.inf, []
    for level in levels:
        peak = max(peak, level)
        out.append((level / peak - 1) * 100 if peak > 0 else 0.0)
    return out


def _cagr(new: Decimal | float, old: Decimal | float, years: float) -> float | None:
    if years <= 0 or old <= 0 or new <= 0:
        return None
    return ((float(new) / float(old)) ** (1 / years) - 1) * 100


def rolling(
    dates: list[date], navs: list[Decimal], years: int, benchmark: History | None
) -> Rolling | None:
    """CAGR over every ``years``-long stretch inside the window, one ending on each date."""
    j, returns, beats, curve = 0, [], [], []
    for i, day in enumerate(dates):
        back = years_before(day, years)
        if back < dates[0]:
            continue
        while j + 1 < len(dates) and dates[j + 1] <= back:
            j += 1
        span = (day - dates[j]).days / 365
        rate = _cagr(navs[i], navs[j], span)
        if rate is None:
            continue
        returns.append(rate)
        curve.append((day, rate))
        if benchmark:
            then, now = benchmark.at(dates[j]), benchmark.at(day)
            if then is not None and now is not None:
                theirs = _cagr(now, then, span)
                if theirs is not None:
                    beats.append(rate > theirs)
    if not returns:
        return None
    return Rolling(
        years=years,
        periods=len(returns),
        median_pct=statistics.median(returns),
        worst_pct=min(returns),
        best_pct=max(returns),
        beat_benchmark_pct=sum(beats) / len(beats) * 100 if beats else None,
        curve=curve,
    )


def _ends(dates: list[date], frequency: str) -> list[int]:
    """The first index, then the last index of every week or month."""
    ends = [0]
    for i in range(1, len(dates)):
        last = i == len(dates) - 1
        if last or engine.period_key(dates[i + 1], frequency) != engine.period_key(
            dates[i], frequency
        ):
            ends.append(i)
    return ends


def _returns(values: list[float], ends: list[int]) -> list[float]:
    return [values[b] / values[a] - 1 for a, b in zip(ends, ends[1:], strict=False)]


def capture(
    dates: list[date], navs: list[Decimal], benchmark: History | None
) -> tuple[float | None, float | None]:
    """Upside and downside capture against the benchmark, from monthly returns: how much of
    the benchmark's rise (fall) the fund had in the months it rose (fell). 100 = the same."""
    if not benchmark or benchmark.first > dates[0]:
        return None, None
    ends = _ends(dates, "monthly")
    mine = _returns([float(nav) for nav in navs], ends)
    theirs = _returns([float(benchmark.at(day) or 0) for day in dates], ends)
    if len(mine) < MIN_MONTHS:
        return None, None

    def ratio(keep) -> float | None:
        pairs = [(m, t) for m, t in zip(mine, theirs, strict=True) if keep(t)]
        if not pairs:
            return None
        n = len(pairs)
        a = math.prod(1 + m for m, _ in pairs) ** (1 / n) - 1
        b = math.prod(1 + t for _, t in pairs) ** (1 / n) - 1
        return a / b * 100 if b else None

    return ratio(lambda t: t > 0), ratio(lambda t: t < 0)


def sip(aligned: engine.Aligned, key: int) -> Sip:
    run = engine.run_sip(aligned, [(key, Decimal(100))], SIP_AMOUNT)
    m = engine.metrics(run.days)
    return Sip(m.total_invested, run.days[-1].value, m.xirr_pct)


def thin(dates: list[date]) -> list[int]:
    """Indexes of the points to draw: all of them, or one a week for long windows."""
    if len(dates) <= CHART_POINTS:
        return list(range(len(dates)))
    return _ends(dates, "weekly")


def over_window(
    aligned: engine.Aligned, key: int, rolling_years: int, benchmark: History | None
) -> WindowFigures:
    dates = aligned.dates[aligned.start :]
    navs: list[Decimal] = aligned.navs[key][aligned.start :]  # type: ignore[assignment]
    days = _days(dates, navs)
    m = engine.metrics(days)
    levels = engine.growth_index(days)
    falls = drawdowns(levels)
    up, down = capture(dates, navs, benchmark)
    drawn = thin(dates)
    worst = m.max_drawdown_pct
    found = rolling(dates, navs, rolling_years, benchmark)
    if found:
        keep = set(thin([day for day, _ in found.curve]))
        found.curve = [point for i, point in enumerate(found.curve) if i in keep]
    return WindowFigures(
        cagr_pct=m.cagr_pct,
        return_pct=float(m.absolute_return_pct) if m.absolute_return_pct is not None else None,
        volatility_pct=m.volatility_pct,
        max_drawdown_pct=worst,
        recovery=recovery(dates, levels),
        calmar=m.cagr_pct / worst if m.cagr_pct is not None and worst > 0 else None,
        upside_capture_pct=up,
        downside_capture_pct=down,
        rolling=found,
        sip=sip(aligned, key),
        growth=[(days[i].date, engine.money(days[i].value)) for i in drawn],
        drawdown=[(dates[i], falls[i]) for i in drawn],
    )


# --- Whole history ---------------------------------------------------------------------


def trailing(history: History, as_of: date, years: int) -> float | None:
    """CAGR over the ``years`` up to ``as_of``; ``None`` if the fund is younger."""
    back = years_before(as_of, years)
    if not history or history.first > back or history.last < as_of:
        return None
    then, now = history.at(back), history.at(as_of)
    return _cagr(now, then, years) if then is not None and now is not None else None


def calendar_years(as_of: date) -> list[int]:
    return list(range(as_of.year - CALENDAR_YEARS + 1, as_of.year + 1))


def calendar(history: History, as_of: date) -> dict[int, float | None]:
    """Each calendar year's return, the last one to ``as_of``. A year the fund wasn't there
    for all of is left blank."""
    out: dict[int, float | None] = {}
    for year in calendar_years(as_of):
        start, stop = date(year - 1, 12, 31), min(date(year, 12, 31), as_of)
        if not history or history.first > start or history.last < stop:
            out[year] = None
            continue
        then, now = history.at(start), history.at(stop)
        out[year] = (float(now) / float(then) - 1) * 100 if then and now else None
    return out


def correlation(aligned: engine.Aligned, keys: list[int]) -> dict[tuple[int, int], float | None]:
    """How closely each pair moved, from weekly returns over the window (1 = in lockstep).
    Weekly, not daily: funds holding foreign shares publish a day late."""
    dates = aligned.dates[aligned.start :]
    ends = _ends(dates, "weekly")
    weekly = {
        key: _returns([float(nav) for nav in aligned.navs[key][aligned.start :]], ends)  # type: ignore[arg-type]
        for key in keys
    }
    out: dict[tuple[int, int], float | None] = {}
    for a in keys:
        for b in keys:
            if a == b:
                out[a, b] = 1.0
            elif (b, a) in out:
                out[a, b] = out[b, a]
            elif len(weekly[a]) < MIN_WEEKS:
                out[a, b] = None
            else:
                try:
                    out[a, b] = statistics.correlation(weekly[a], weekly[b])
                except statistics.StatisticsError:  # a fund that never moved
                    out[a, b] = None
    return out
