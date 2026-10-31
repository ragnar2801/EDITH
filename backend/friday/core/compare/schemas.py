"""What a comparison of funds, buckets or models returns. Figures are rounded decimal
strings; curves are for drawing only."""

from datetime import date

from pydantic import BaseModel

from friday.core.schema_types import Amount, Figure, Percent


class GrowthPoint(BaseModel):
    date: date
    value: Amount


class PercentPoint(BaseModel):
    date: date
    value: Percent


class TrailingOut(BaseModel):
    """CAGR over the years up to the comparison's ``as_of`` date."""

    y1: Percent | None
    y3: Percent | None
    y5: Percent | None
    y10: Percent | None


class CalendarReturn(BaseModel):
    year: int
    return_pct: Percent | None
    """Blank for a year the fund wasn't there for all of."""


class RollingOut(BaseModel):
    years: int
    periods: int
    median_pct: Percent
    worst_pct: Percent
    best_pct: Percent
    beat_benchmark_pct: Percent | None
    curve: list[PercentPoint]


class SipResult(BaseModel):
    invested: Amount
    value: Amount
    xirr_pct: Percent | None


class WindowFiguresOut(BaseModel):
    cagr_pct: Percent | None
    return_pct: Percent | None
    volatility_pct: Percent
    max_drawdown_pct: Percent
    recovery_days: int | None
    """From the peak before the largest fall until back at it (or until the window's end)."""
    recovered: bool | None
    calmar: Figure | None
    upside_capture_pct: Percent | None
    downside_capture_pct: Percent | None
    rolling: RollingOut | None
    sip: SipResult
    growth: list[GrowthPoint]
    drawdown: list[PercentPoint]


class Compared(BaseModel):
    """One fund, bucket or model (or the benchmark), by its id."""

    id: int
    first: date | None
    """The first date with a value; ``None`` when there is none yet."""
    last: date | None
    trailing: TrailingOut
    calendar: list[CalendarReturn]
    window: WindowFiguresOut | None
    """``None`` when it doesn't cover the window."""


class BucketMoney(BaseModel):
    """What the money in a bucket did, as Portfolio shows it."""

    invested: Amount
    value: Amount
    gain: Amount
    return_pct: Percent | None
    xirr_pct: Percent | None
    """Shown once the first money has been in a year."""


class ComparedBucket(Compared):
    money: BucketMoney | None
    """``None`` when nothing in the bucket has a NAV yet."""


class WindowOut(BaseModel):
    start: date
    end: date
    years: Figure
    limited_by: int | None
    """The youngest in the window, when leaving it out would start the window earlier."""
    earliest_start: date | None
    """Where the window would start without ``limited_by``."""


BENCHMARK = 0
"""The benchmark's id in :class:`Correlation` pairs."""


class Correlation(BaseModel):
    a: int
    """An id of :attr:`Comparison.items`, or :data:`BENCHMARK`."""
    b: int
    value: Figure | None


class Comparison(BaseModel):
    window: WindowOut | None
    """``None`` when they share no dates."""
    as_of: date | None
    """The date trailing and calendar-year returns run to: the window's end."""
    rolling_years: int
    items: list[Compared]
    """In the order picked."""
    benchmark: Compared | None
    """A fund; its ``id`` is the instrument's."""
    calendar_years: list[int]
    correlation: list[Correlation]
    """Each pair in the window (and the benchmark, if it covers it) once."""
    warnings: list[str]


class BucketComparison(Comparison):
    items: list[ComparedBucket]
