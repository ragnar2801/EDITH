"""What a comparison of funds returns. Figures are rounded decimal strings; curves are for
drawing only."""

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


class ComparedFund(BaseModel):
    instrument_id: int
    first_nav: date | None
    last_nav: date | None
    trailing: TrailingOut
    calendar: list[CalendarReturn]
    window: WindowFiguresOut | None
    """``None`` when the fund doesn't cover the window."""


class WindowOut(BaseModel):
    start: date
    end: date
    years: Figure
    limited_by: int | None
    """The youngest fund in the window, when leaving it out would start the window earlier."""
    earliest_start: date | None
    """Where the window would start without ``limited_by``."""


class Correlation(BaseModel):
    a: int
    b: int
    value: Figure | None


class Comparison(BaseModel):
    window: WindowOut | None
    """``None`` when the funds share no dates."""
    as_of: date | None
    """The date trailing and calendar-year returns run to: the window's end."""
    rolling_years: int
    funds: list[ComparedFund]
    benchmark: ComparedFund | None
    calendar_years: list[int]
    correlation: list[Correlation]
    """Each pair of funds in the window (and the benchmark, if it covers it) once."""
    warnings: list[str]
