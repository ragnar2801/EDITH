"""Compare funds on their stored NAVs: over the dates they share, and against a benchmark."""

from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from friday.core.backtest import engine
from friday.core.backtest.service import despiked_series
from friday.core.compare import figures
from friday.core.compare.figures import History
from friday.core.compare.schemas import (
    CalendarReturn,
    ComparedFund,
    Comparison,
    Correlation,
    GrowthPoint,
    PercentPoint,
    RollingOut,
    SipResult,
    TrailingOut,
    WindowFiguresOut,
    WindowOut,
)
from friday.core.instruments.models import Instrument
from friday.core.models.service import default_benchmark
from friday.core.navs.service import require_fund

MAX_FUNDS = 20
ROLLING_YEARS = (1, 3, 5, 10)


class CompareError(ValueError):
    """The comparison can't be made with these inputs."""


def _pct(value: float | Decimal | None) -> Decimal | None:
    return engine.figure(value)


def _window_out(found: figures.WindowFigures) -> WindowFiguresOut:
    rolling = found.rolling
    return WindowFiguresOut(
        cagr_pct=_pct(found.cagr_pct),
        return_pct=_pct(found.return_pct),
        volatility_pct=_pct(found.volatility_pct),
        max_drawdown_pct=_pct(found.max_drawdown_pct),
        recovery_days=found.recovery.days if found.recovery else None,
        recovered=found.recovery.recovered if found.recovery else None,
        calmar=_pct(found.calmar),
        upside_capture_pct=_pct(found.upside_capture_pct),
        downside_capture_pct=_pct(found.downside_capture_pct),
        rolling=RollingOut(
            years=rolling.years,
            periods=rolling.periods,
            median_pct=_pct(rolling.median_pct),
            worst_pct=_pct(rolling.worst_pct),
            best_pct=_pct(rolling.best_pct),
            beat_benchmark_pct=_pct(rolling.beat_benchmark_pct),
            curve=[PercentPoint(date=day, value=_pct(value)) for day, value in rolling.curve],
        )
        if rolling
        else None,
        sip=SipResult(
            invested=engine.money(found.sip.invested),
            value=engine.money(found.sip.value),
            xirr_pct=_pct(found.sip.xirr_pct),
        ),
        growth=[GrowthPoint(date=day, value=value) for day, value in found.growth],
        drawdown=[PercentPoint(date=day, value=_pct(value)) for day, value in found.drawdown],
    )


def _fund(
    key: int,
    history: History,
    as_of: date | None,
    window: WindowFiguresOut | None,
) -> ComparedFund:
    trailing = {
        f"y{years}": _pct(figures.trailing(history, as_of, years)) if as_of else None
        for years in figures.TRAILING_YEARS
    }
    calendar = figures.calendar(history, as_of) if as_of else {}
    return ComparedFund(
        instrument_id=key,
        first_nav=history.first if history else None,
        last_nav=history.last if history else None,
        trailing=TrailingOut(**trailing),
        calendar=[
            CalendarReturn(year=year, return_pct=_pct(value)) for year, value in calendar.items()
        ],
        window=window,
    )


def _instrument(session: Session, instrument_id: int) -> Instrument:
    instrument = session.get(Instrument, instrument_id)
    if instrument is None:
        raise LookupError(f"No instrument with id {instrument_id}.")
    try:
        require_fund(instrument)
    except ValueError as error:
        raise CompareError(str(error)) from None
    return instrument


def compare_funds(
    session: Session,
    ids: list[int],
    *,
    benchmark_id: int | None = None,
    start: date | None = None,
    end: date | None = None,
    rolling_years: int = 3,
) -> Comparison:
    """Compare ``ids`` (in that order) over the dates they share, or from ``start`` for the
    funds that go back that far. The benchmark is ``benchmark_id`` or the default one.
    Raises :class:`LookupError` for an unknown id, :class:`CompareError` for bad inputs."""
    ids = list(dict.fromkeys(ids))
    if not ids:
        raise CompareError("Pick at least one fund.")
    if len(ids) > MAX_FUNDS:
        raise CompareError(f"Compare at most {MAX_FUNDS} funds at a time.")
    if rolling_years not in ROLLING_YEARS:
        raise CompareError(f"Rolling returns cover {', '.join(map(str, ROLLING_YEARS))} years.")
    if start and end and start >= end:
        raise CompareError("The start must be before the end.")

    warnings: list[str] = []
    instruments = {key: _instrument(session, key) for key in ids}
    histories = {
        key: History(despiked_series(session, instrument, warnings))
        for key, instrument in instruments.items()
    }
    bench = _instrument(session, benchmark_id) if benchmark_id else default_benchmark(session)
    bench_history = History(despiked_series(session, bench, warnings)) if bench else None
    for key, history in histories.items():
        if not history:
            warnings.append(f"{instruments[key].name} has no NAVs yet.")
    if bench and not bench_history:
        warnings.append(f"Benchmark {bench.name} has no NAVs yet.")

    found = figures.window(histories, start, end)
    windowed: dict[int, WindowFiguresOut] = {}
    bench_window = None
    correlation: list[Correlation] = []
    if found:
        series = {key: histories[key].points for key in found.members}
        aligned = engine.align(series, found.start, found.end)
        for key in found.members:
            windowed[key] = _window_out(
                figures.over_window(aligned, key, rolling_years, bench_history)
            )
        keys = list(found.members)
        if bench and bench_history and bench_history.first <= found.start:
            # Drawn on the funds' dates: the benchmark mustn't change the funds' figures.
            alone = engine.align({bench.id: bench_history.points}, found.start, found.end)
            bench_window = _window_out(figures.over_window(alone, bench.id, rolling_years, None))
            if bench.id not in series:
                series[bench.id] = bench_history.points
                keys.append(bench.id)
        elif bench and bench_history:
            warnings.append(
                f"Benchmark {bench.name} starts on {bench_history.first.isoformat()}, after "
                "the window, so it's left out of the window's figures."
            )
        pairs = figures.correlation(engine.align(series, found.start, found.end), keys)
        correlation = [
            Correlation(a=a, b=b, value=_pct(pairs[a, b]))
            for i, a in enumerate(keys)
            for b in keys[i + 1 :]
        ]
        as_of: date | None = found.end
    else:
        lasts = [history.last for history in histories.values() if history]
        as_of = min(lasts) if lasts else None
        if lasts:
            warnings.append("These funds have no NAV dates in common.")

    return Comparison(
        window=WindowOut(
            start=found.start,
            end=found.end,
            years=engine.figure((found.end - found.start).days / 365),
            limited_by=found.limited_by,
            earliest_start=found.earliest_start,
        )
        if found
        else None,
        as_of=as_of,
        rolling_years=rolling_years,
        funds=[_fund(key, histories[key], as_of, windowed.get(key)) for key in ids],
        benchmark=_fund(bench.id, bench_history, as_of, bench_window)
        if bench and bench_history is not None
        else None,
        calendar_years=figures.calendar_years(as_of) if as_of else [],
        correlation=correlation,
        warnings=warnings,
    )
