"""Run a backtest of a bucket on its stored NAVs, keep the run, and slice it (D-048, D-049)."""

from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from friday.core.backtest import engine
from friday.core.backtest.engine import CustomTrade, Day, EngineError
from friday.core.backtest.models import BacktestRun
from friday.core.backtest.schemas import (
    BacktestParams,
    BacktestResult,
    BenchmarkOut,
    CurvePoint,
    CustomParams,
    FundOutcomeOut,
    IntervalOut,
    MetricsOut,
    RegularParams,
    SipParams,
    SwpParams,
    TradeOut,
)
from friday.core.buckets.models import Bucket
from friday.core.instruments.models import Instrument
from friday.core.navs.service import nav_series

KEEP_UNSAVED = 20
"""Unsaved runs kept, newest first; older ones are deleted (D-049)."""


def _compile(params: CustomParams, members: set[int]) -> list[CustomTrade]:
    """Positions are shorthand: a buy at entry and, if given, a sell of everything at exit."""
    trades: list[CustomTrade] = []
    for number, position in enumerate(params.positions, 1):
        if position.instrument_id not in members:
            raise EngineError(f"position {number}: that fund isn't in this bucket")
        trades.append(
            CustomTrade(position.instrument_id, position.entry, "buy", amount=position.amount)
        )
        if position.exit:
            trades.append(CustomTrade(position.instrument_id, position.exit, "sell", sell_all=True))
    for number, trade in enumerate(params.trades, 1):
        if trade.instrument_id not in members:
            raise EngineError(f"trade {number}: that fund isn't in this bucket")
        trades.append(
            CustomTrade(
                trade.instrument_id,
                trade.date,
                trade.side,
                amount=trade.amount,
                units=trade.units,
                sell_all=trade.sell_all,
            )
        )
    return sorted(trades, key=lambda trade: (trade.date, trade.side != "sell"))


def _series(session: Session, instrument: Instrument, warnings: list[str]) -> engine.Series:
    points, replaced = engine.despike(nav_series(session, instrument.id))
    if replaced:
        warnings.append(
            f"{instrument.name}: {replaced} NAV{'s' if replaced > 1 else ''} looked like bad "
            "data (over 1.8× or under 0.55× the NAVs around it) and were replaced by the "
            "middle of their neighbours."
        )
    return points


def _curve(days: list[Day]) -> list[CurvePoint]:
    index = engine.growth_index(days)
    return [
        CurvePoint(
            date=day.date,
            value=engine.money(day.value),
            invested=engine.money(day.invested),
            withdrawn=engine.money(day.withdrawn),
            index=engine.figure(level, 6),
        )
        for day, level in zip(days, index, strict=True)
    ]


def _metrics(days: list[Day], risk_free_pct: Decimal, depletion: date | None) -> MetricsOut:
    m = engine.metrics(days, risk_free_pct, depletion)
    return MetricsOut(
        start_date=m.start_date,
        end_date=m.end_date,
        years=engine.figure(m.years),
        start_value=engine.money(m.start_value),
        end_value=engine.money(m.end_value),
        total_invested=engine.money(m.total_invested),
        total_withdrawn=engine.money(m.total_withdrawn),
        absolute_return_pct=engine.figure(m.absolute_return_pct),
        cagr_pct=engine.figure(m.cagr_pct),
        xirr_pct=engine.figure(m.xirr_pct),
        max_drawdown_pct=engine.figure(m.max_drawdown_pct),
        volatility_pct=engine.figure(m.volatility_pct),
        sharpe=engine.figure(m.sharpe),
        sortino=engine.figure(m.sortino),
        depletion_date=m.depletion_date,
    )


def _units(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.00000001"))


def _outcome(outcome: engine.FundOutcome, name: str) -> FundOutcomeOut:
    pnl = pnl_pct = None
    if outcome.invested is not None:
        pnl = outcome.proceeds + outcome.end_value - outcome.invested
        pnl_pct = engine.figure(pnl / outcome.invested * 100) if outcome.invested else None
    return FundOutcomeOut(
        instrument_id=outcome.instrument_id,
        name=name,
        weight=outcome.weight,
        units=_units(outcome.units),
        end_value=engine.money(outcome.end_value),
        invested=engine.money(outcome.invested) if outcome.invested is not None else None,
        proceeds=engine.money(outcome.proceeds) if outcome.proceeds is not None else None,
        pnl=engine.money(pnl) if pnl is not None else None,
        pnl_pct=pnl_pct,
    )


def run_backtest(session: Session, bucket: Bucket, params: BacktestParams) -> BacktestResult:
    """Run ``params`` on the bucket's stored NAVs. Raises :class:`EngineError` when it can't."""
    members = {member.instrument_id: member for member in bucket.funds}
    names = {fund_id: member.instrument.name for fund_id, member in members.items()}
    warnings: list[str] = []

    if isinstance(params, CustomParams):
        trades = _compile(params, set(members))
        fund_ids = list(dict.fromkeys(trade.instrument_id for trade in trades))
    else:
        trades = []
        fund_ids = list(members)
    series = {
        fund_id: _series(session, members[fund_id].instrument, warnings) for fund_id in fund_ids
    }
    missing = [names[fund_id] for fund_id, points in series.items() if not points]
    if missing:
        raise EngineError(f"no NAVs yet for {', '.join(missing)}; sync NAVs first")

    if isinstance(params, CustomParams):
        aligned = engine.align(series, end=params.end)
        run = engine.run_custom(aligned, trades, names)
    else:
        aligned = engine.align(series, params.start, params.end)
        weights = [(fund_id, members[fund_id].weight_pct) for fund_id in fund_ids]
        if isinstance(params, RegularParams):
            rebalance = params.rebalance or bucket.rebalance
            run = engine.run_regular(aligned, weights, params.capital, rebalance)
        elif isinstance(params, SipParams):
            run = engine.run_sip(aligned, weights, params.amount, params.frequency)
        elif isinstance(params, SwpParams):
            run = engine.run_swp(aligned, weights, params.corpus, params.amount, params.frequency)
        else:  # pragma: no cover (the union is closed)
            raise EngineError(f"unknown strategy {params.strategy}")
        began = aligned.dates[aligned.start]
        if params.start and began > params.start:
            youngest = max(fund_ids, key=lambda fund_id: series[fund_id][0][0])
            warnings.append(
                f"Started on {began.isoformat()} instead of {params.start.isoformat()}: "
                f"{names[youngest]} has no NAV before then."
            )
    warnings.extend(run.warnings)

    benchmark = None
    if bucket.benchmark is not None:
        bench_series = _series(session, bucket.benchmark, warnings)
        bench_days = engine.replay_flows(bench_series, run.days) if bench_series else None
        if bench_days is None:
            warnings.append(
                f"Benchmark left out: {bucket.benchmark.name} has no NAV on "
                f"{run.days[0].date.isoformat()}."
            )
        else:
            benchmark = BenchmarkOut(
                instrument_id=bucket.benchmark.id,
                name=bucket.benchmark.name,
                curve=_curve(bench_days),
                metrics=_metrics(bench_days, params.risk_free_pct, None),
            )

    return BacktestResult(
        strategy=params.strategy,
        curve=_curve(run.days),
        metrics=_metrics(run.days, params.risk_free_pct, run.depletion_date),
        funds=[_outcome(outcome, names[outcome.instrument_id]) for outcome in run.funds],
        trades=[
            TradeOut(
                date=trade.date,
                instrument_id=trade.instrument_id,
                name=names[trade.instrument_id],
                side=trade.side,
                units=_units(trade.units),
                nav=trade.nav,
                amount=engine.money(trade.amount),
            )
            for trade in run.trades
        ],
        benchmark=benchmark,
        warnings=warnings,
    )


def store_run(
    session: Session,
    bucket: Bucket,
    params: BacktestParams,
    result: BacktestResult,
    *,
    saved: bool = False,
    name: str | None = None,
) -> BacktestRun:
    run = BacktestRun(
        bucket_id=bucket.id,
        strategy=params.strategy,
        params=params.model_dump_json(),
        result=result.model_dump_json(),
        saved=saved,
        name=name,
        created_at=datetime.now(UTC),
    )
    session.add(run)
    session.flush()
    old = session.scalars(
        select(BacktestRun)
        .where(BacktestRun.saved.is_(False))
        .order_by(BacktestRun.id.desc())
        .offset(KEEP_UNSAVED)
    ).all()
    for stale in old:
        session.delete(stale)
    session.flush()
    return run


def saved_runs(session: Session, bucket_id: int) -> list[BacktestRun]:
    return list(
        session.scalars(
            select(BacktestRun)
            .where(BacktestRun.bucket_id == bucket_id, BacktestRun.saved.is_(True))
            .order_by(BacktestRun.id.desc())
        )
    )


def _days(curve: list[CurvePoint]) -> list[Day]:
    days, previous = [], None
    for point in curve:
        flow = point.invested - point.withdrawn
        if previous is not None:
            flow -= previous.invested - previous.withdrawn
        days.append(Day(point.date, point.value, point.invested, point.withdrawn, flow))
        previous = point
    return days


def run_interval(
    result: BacktestResult, start: date | None, end: date | None
) -> IntervalOut | None:
    """Figures for a window of a stored run (D-049), with the benchmark's return over it."""
    window = engine.interval(_days(result.curve), start, end)
    if window is None:
        return None
    bench = (
        engine.interval(_days(result.benchmark.curve), window.start_date, window.end_date)
        if result.benchmark
        else None
    )
    return IntervalOut(
        start_date=window.start_date,
        end_date=window.end_date,
        start_value=engine.money(window.start_value),
        end_value=engine.money(window.end_value),
        return_pct=engine.figure(window.return_pct),
        max_drawdown_pct=engine.figure(window.max_drawdown_pct),
        invested=engine.money(window.invested),
        withdrawn=engine.money(window.withdrawn),
        benchmark_return_pct=engine.figure(bench.return_pct) if bench else None,
    )
