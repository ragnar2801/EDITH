"""Compare funds, buckets or models over the dates they share, and against a benchmark.

Each one becomes a series that works like a NAV: a fund's NAVs, a bucket's time-weighted
growth, a model's lump sum split by its weights. The same figures then apply to all three.
"""

from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from friday.core.backtest import engine
from friday.core.backtest.service import despiked_series
from friday.core.buckets.models import Bucket
from friday.core.compare import figures
from friday.core.compare.figures import History
from friday.core.compare.schemas import (
    BENCHMARK,
    BucketComparison,
    BucketMoney,
    CalendarReturn,
    Compared,
    ComparedBucket,
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
from friday.core.models.models import Model
from friday.core.models.service import default_benchmark
from friday.core.navs.service import require_fund
from friday.core.portfolio.returns import Returns
from friday.core.portfolio.service import growth, portfolio

MAX_ITEMS = 20
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


def _compared(
    key: int,
    history: History,
    as_of: date | None,
    window: WindowFiguresOut | None,
) -> Compared:
    trailing = {
        f"y{years}": _pct(figures.trailing(history, as_of, years)) if as_of else None
        for years in figures.TRAILING_YEARS
    }
    calendar = figures.calendar(history, as_of) if as_of else {}
    return Compared(
        id=key,
        first=history.first if history else None,
        last=history.last if history else None,
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


def _check(
    ids: list[int], noun: str, rolling_years: int, start: date | None, end: date | None
) -> list[int]:
    ids = list(dict.fromkeys(ids))
    if not ids:
        raise CompareError(f"Pick at least one {noun}.")
    if len(ids) > MAX_ITEMS:
        raise CompareError(f"Compare at most {MAX_ITEMS} {noun}s at a time.")
    if rolling_years not in ROLLING_YEARS:
        raise CompareError(f"Rolling returns cover {', '.join(map(str, ROLLING_YEARS))} years.")
    if start and end and start >= end:
        raise CompareError("The start must be before the end.")
    return ids


def _benchmark(
    session: Session, benchmark_id: int | None, warnings: list[str]
) -> tuple[Instrument | None, History | None]:
    bench = _instrument(session, benchmark_id) if benchmark_id else default_benchmark(session)
    if bench is None:
        return None, None
    history = History(despiked_series(session, bench, warnings))
    if not history:
        warnings.append(f"Benchmark {bench.name} has no NAVs yet.")
    return bench, history


def _compare(
    histories: dict[int, History],
    bench: Instrument | None,
    bench_history: History | None,
    *,
    start: date | None,
    end: date | None,
    rolling_years: int,
    warnings: list[str],
) -> Comparison:
    """Compare ``histories`` (in that order) over the dates they share, or from ``start``
    for the ones that go back that far. Each history works like a NAV: only its moves count.
    """
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
            # On its own dates: the benchmark mustn't change the others' figures.
            alone = engine.align({BENCHMARK: bench_history.points}, found.start, found.end)
            bench_window = _window_out(figures.over_window(alone, BENCHMARK, rolling_years, None))
            series[BENCHMARK] = bench_history.points
            keys.append(BENCHMARK)
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
            warnings.append("They have no dates in common.")

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
        items=[
            _compared(key, history, as_of, windowed.get(key)) for key, history in histories.items()
        ],
        benchmark=_compared(bench.id, bench_history, as_of, bench_window)
        if bench and bench_history is not None
        else None,
        calendar_years=figures.calendar_years(as_of) if as_of else [],
        correlation=correlation,
        warnings=warnings,
    )


def compare_funds(
    session: Session,
    ids: list[int],
    *,
    benchmark_id: int | None = None,
    start: date | None = None,
    end: date | None = None,
    rolling_years: int = 3,
) -> Comparison:
    """Compare funds on their NAVs. The benchmark is ``benchmark_id`` or the default one.
    Raises :class:`LookupError` for an unknown id, :class:`CompareError` for bad inputs."""
    ids = _check(ids, "fund", rolling_years, start, end)
    warnings: list[str] = []
    instruments = {key: _instrument(session, key) for key in ids}
    bench, bench_history = _benchmark(session, benchmark_id, warnings)
    histories = {
        key: History(despiked_series(session, instrument, warnings))
        for key, instrument in instruments.items()
    }
    for key, history in histories.items():
        if not history:
            warnings.append(f"{instruments[key].name} has no NAVs yet.")
    return _compare(
        histories,
        bench,
        bench_history,
        start=start,
        end=end,
        rolling_years=rolling_years,
        warnings=warnings,
    )


def model_growth(session: Session, model: Model, warnings: list[str]) -> engine.Series:
    """``CAPITAL`` split by the model's weights on the first date all its funds have a NAV,
    rebalanced as the model says. Empty (with a warning) when that date doesn't exist."""
    series = {
        m.instrument_id: despiked_series(session, m.instrument, warnings) for m in model.funds
    }
    missing = [m.instrument.name for m in model.funds if not series[m.instrument_id]]
    if missing:
        warnings.append(f"{model.name}: no NAVs yet for {', '.join(missing)}.")
        return []
    aligned = engine.align(series)
    if aligned.start >= len(aligned.dates):
        warnings.append(f"{model.name}: its funds have no NAV dates in common.")
        return []
    weights = [(m.instrument_id, m.weight_pct) for m in model.funds]
    run = engine.run_regular(aligned, weights, figures.CAPITAL, model.rebalance)
    return [(day.date, day.value) for day in run.days]


def compare_models(
    session: Session,
    ids: list[int],
    *,
    benchmark_id: int | None = None,
    start: date | None = None,
    end: date | None = None,
    rolling_years: int = 3,
) -> Comparison:
    """Compare models as if each were one fund: a lump sum split by its weights and
    rebalanced as it says (:func:`model_growth`)."""
    ids = _check(ids, "model", rolling_years, start, end)
    models = {}
    for key in ids:
        model = session.get(Model, key)
        if model is None:
            raise LookupError(f"No model with id {key}.")
        models[key] = model
    warnings: list[str] = []
    bench, bench_history = _benchmark(session, benchmark_id, warnings)
    histories = {
        key: History(model_growth(session, model, warnings)) for key, model in models.items()
    }
    return _compare(
        histories,
        bench,
        bench_history,
        start=start,
        end=end,
        rolling_years=rolling_years,
        warnings=warnings,
    )


def _money(returns: Returns | None) -> BucketMoney | None:
    if returns is None:
        return None
    return BucketMoney(
        invested=returns.invested,
        value=returns.value,
        gain=returns.gain,
        return_pct=returns.return_pct,
        xirr_pct=returns.xirr_pct,
    )


def compare_buckets(
    session: Session,
    ids: list[int],
    *,
    benchmark_id: int | None = None,
    start: date | None = None,
    end: date | None = None,
    rolling_years: int = 3,
) -> BucketComparison:
    """Compare buckets on their time-weighted growth (:func:`portfolio.service.growth`), so
    when the money went in doesn't count; what it made is in each bucket's ``money``."""
    ids = _check(ids, "bucket", rolling_years, start, end)
    buckets = {}
    for key in ids:
        bucket = session.get(Bucket, key)
        if bucket is None:
            raise LookupError(f"No bucket with id {key}.")
        buckets[key] = bucket
    warnings: list[str] = []
    bench, bench_history = _benchmark(session, benchmark_id, warnings)
    histories = {key: History(growth(session, bucket)) for key, bucket in buckets.items()}
    for key, history in histories.items():
        if not history:
            warnings.append(f"{buckets[key].name} has no purchases with a NAV yet.")
    found = _compare(
        histories,
        bench,
        bench_history,
        start=start,
        end=end,
        rolling_years=rolling_years,
        warnings=warnings,
    )
    return BucketComparison(
        **found.model_dump(exclude={"items"}),
        items=[
            ComparedBucket(
                **item.model_dump(), money=_money(portfolio(session, buckets[item.id]).returns)
            )
            for item in found.items
        ],
    )
