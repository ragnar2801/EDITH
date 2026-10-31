"""Run a backtest of a model on its stored NAVs, keep the run, slice it, compare two runs and
search every split of its funds."""

import math
from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from friday.core.backtest import engine, search
from friday.core.backtest.engine import CustomTrade, Day, EngineError
from friday.core.backtest.models import BacktestRun
from friday.core.backtest.schemas import (
    BacktestParams,
    BacktestResult,
    BenchmarkOut,
    Candidate,
    CandidateFund,
    ComparisonOut,
    CurvePoint,
    CustomParams,
    FundOutcomeOut,
    IntervalOut,
    MetricsOut,
    OptimiseOut,
    RegularParams,
    SearchPoint,
    SearchSettings,
    SipParams,
    SwpParams,
    TradeOut,
    WeightChange,
    WeightedParams,
)
from friday.core.instruments.models import Instrument
from friday.core.models.models import Model
from friday.core.models.service import InvalidModel, check_split
from friday.core.navs.service import nav_series

KEEP_UNSAVED = 20
"""Unsaved runs kept, newest first; older ones are deleted."""
TOP = 10
"""Splits the search shows, re-run with the engine."""


def _compile(params: CustomParams, members: set[int]) -> list[CustomTrade]:
    """Positions are shorthand: a buy at entry and, if given, a sell of everything at exit."""
    trades: list[CustomTrade] = []
    for number, position in enumerate(params.positions, 1):
        if position.instrument_id not in members:
            raise EngineError(f"position {number}: that fund isn't in this model")
        trades.append(
            CustomTrade(position.instrument_id, position.entry, "buy", amount=position.amount)
        )
        if position.exit:
            trades.append(CustomTrade(position.instrument_id, position.exit, "sell", sell_all=True))
    for number, trade in enumerate(params.trades, 1):
        if trade.instrument_id not in members:
            raise EngineError(f"trade {number}: that fund isn't in this model")
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


def despiked_series(session: Session, instrument: Instrument, warnings: list[str]) -> engine.Series:
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


def _split(
    session: Session, model: Model, params: BacktestParams
) -> dict[int, tuple[Instrument, Decimal]]:
    """Fund id → (fund, weight): the split ``params`` tries, else the model's own."""
    if not isinstance(params, WeightedParams) or params.split is None:
        return {m.instrument_id: (m.instrument, m.weight_pct) for m in model.funds}
    funds = [(fund.instrument_id, fund.weight) for fund in params.split]
    try:
        instruments = check_split(session, funds)
    except InvalidModel as error:
        raise EngineError(f"split: {error}") from None
    return {fund.id: (fund, weight) for fund, (_, weight) in zip(instruments, funds, strict=True)}


def run_backtest(session: Session, model: Model, params: BacktestParams) -> BacktestResult:
    """Run ``params`` on the model's stored NAVs. Raises :class:`EngineError` when it can't."""
    members = _split(session, model, params)
    names = {fund_id: fund.name for fund_id, (fund, _) in members.items()}
    warnings: list[str] = []

    if isinstance(params, CustomParams):
        trades = _compile(params, set(members))
        fund_ids = list(dict.fromkeys(trade.instrument_id for trade in trades))
    else:
        trades = []
        fund_ids = list(members)
    series = {
        fund_id: despiked_series(session, members[fund_id][0], warnings) for fund_id in fund_ids
    }
    missing = [names[fund_id] for fund_id, points in series.items() if not points]
    if missing:
        raise EngineError(f"no NAVs yet for {', '.join(missing)}; sync NAVs first")

    if isinstance(params, CustomParams):
        aligned = engine.align(series, end=params.end)
        run = engine.run_custom(aligned, trades, names)
    else:
        aligned = engine.align(series, params.start, params.end)
        weights = [(fund_id, members[fund_id][1]) for fund_id in fund_ids]
        if isinstance(params, RegularParams):
            rebalance = params.rebalance or model.rebalance
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
    if model.benchmark is not None:
        bench_series = despiked_series(session, model.benchmark, warnings)
        bench_days = engine.replay_flows(bench_series, run.days) if bench_series else None
        if bench_days is None:
            warnings.append(
                f"Benchmark left out: {model.benchmark.name} has no NAV on "
                f"{run.days[0].date.isoformat()}."
            )
        else:
            benchmark = BenchmarkOut(
                instrument_id=model.benchmark.id,
                name=model.benchmark.name,
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
    model: Model,
    params: BacktestParams,
    result: BacktestResult,
    *,
    saved: bool = False,
    name: str | None = None,
) -> BacktestRun:
    run = BacktestRun(
        model_id=model.id,
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


def saved_runs(session: Session, model_id: int) -> list[BacktestRun]:
    return list(
        session.scalars(
            select(BacktestRun)
            .where(BacktestRun.model_id == model_id, BacktestRun.saved.is_(True))
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
    """Figures for a window of a stored run, with the benchmark's return over it."""
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


def compare_runs(
    params: BacktestParams,
    result: BacktestResult,
    against: int,
    earlier_params: BacktestParams,
    earlier: BacktestResult,
) -> ComparisonOut:
    """A run less an earlier one: what a change of split (or anything else) did."""
    now, then = result.metrics, earlier.metrics

    def change(a: Decimal | None, b: Decimal | None) -> Decimal | None:
        return None if a is None or b is None else engine.figure(a - b)

    before = {fund.instrument_id: fund for fund in earlier.funds}
    after = {fund.instrument_id: fund for fund in result.funds}
    weights = [
        WeightChange(
            instrument_id=fund_id,
            name=fund.name,
            before=before[fund_id].weight if fund_id in before else None,
            after=fund.weight,
        )
        for fund_id, fund in after.items()
        if fund_id not in before or before[fund_id].weight != fund.weight
    ] + [
        WeightChange(instrument_id=fund_id, name=fund.name, before=fund.weight, after=None)
        for fund_id, fund in before.items()
        if fund_id not in after
    ]
    return ComparisonOut(
        against=against,
        same_settings=params.model_dump(exclude={"split"})
        == earlier_params.model_dump(exclude={"split"}),
        end_value=engine.money(now.end_value - then.end_value),
        xirr_pct=change(now.xirr_pct, then.xirr_pct),
        cagr_pct=change(now.cagr_pct, then.cagr_pct),
        absolute_return_pct=change(now.absolute_return_pct, then.absolute_return_pct),
        max_drawdown_pct=engine.figure(now.max_drawdown_pct - then.max_drawdown_pct),
        volatility_pct=engine.figure(now.volatility_pct - then.volatility_pct),
        sharpe=change(now.sharpe, then.sharpe),
        weights=weights,
    )


def _better(goal: str, candidate: Candidate) -> tuple[float, float]:
    """Sort key: best first for ``goal``, the same order as the search's ranking."""
    m = candidate.metrics
    xirr = float(m.xirr_pct) if m.xirr_pct is not None else -math.inf
    drawdown = float(m.max_drawdown_pct)
    if goal == "xirr":
        return (-xirr, drawdown)
    if goal == "drawdown":
        return (drawdown, -xirr)
    return (-(float(m.sharpe) if m.sharpe is not None else -math.inf), drawdown)


def optimise(
    session: Session,
    model: Model,
    params: RegularParams | SipParams,
    settings: SearchSettings,
) -> OptimiseOut:
    """Try every split of the model's funds on the weight grid, rank them for the goal, and
    re-run the best and the model's own split with the engine."""
    if params.split is not None:
        raise EngineError("the search tries the splits itself; leave the split out")
    members = model.funds
    if len(members) > search.MAX_FUNDS:
        raise EngineError(f"the search works on models of up to {search.MAX_FUNDS} funds")
    count = search.count_splits(
        len(members), settings.step, settings.min_weight, settings.max_weight
    )
    if count == 0:
        raise EngineError("no split with these weights adds up to 100")
    if count > search.MAX_SPLITS:
        raise EngineError(
            f"that is {count:,} splits and the most is {search.MAX_SPLITS:,}; "
            "use a bigger step or a narrower range of weights"
        )

    warnings: list[str] = []
    ids = [member.instrument_id for member in members]
    names = {member.instrument_id: member.instrument.name for member in members}
    series = {m.instrument_id: despiked_series(session, m.instrument, warnings) for m in members}
    missing = [names[fund_id] for fund_id, points in series.items() if not points]
    if missing:
        raise EngineError(f"no NAVs yet for {', '.join(missing)}; sync NAVs first")
    aligned = engine.align(series, params.start, params.end)
    if aligned.start >= len(aligned.dates) - 1:
        raise EngineError("the funds have no NAVs in common for these dates")
    if isinstance(params, RegularParams):
        period = params.rebalance or model.rebalance
        plan = search.Plan("regular", float(params.capital), period)
    else:
        plan = search.Plan("sip", float(params.amount), params.frequency)

    splits = search.grid(len(members), settings.step, settings.min_weight, settings.max_weight)
    measures = search.measure(aligned, ids, splits, plan, float(params.risk_free_pct))
    limit = settings.max_drawdown_pct
    floor = settings.min_xirr_pct
    eligible, best = search.rank(
        measures,
        settings.goal,
        float(limit) if limit is not None else None,
        float(floor) if floor is not None else None,
        TOP,
    )

    def exact(weights: list[tuple[int, Decimal]]) -> tuple[Candidate, list[Day]]:
        held = [(fund_id, weight) for fund_id, weight in weights if weight > 0]
        if isinstance(params, RegularParams):
            run = engine.run_regular(aligned, held, params.capital, period)
        else:
            run = engine.run_sip(aligned, held, params.amount, params.frequency)
        funds = [CandidateFund(instrument_id=i, name=names[i], weight=w) for i, w in held]
        metrics = _metrics(run.days, params.risk_free_pct, None)
        return Candidate(funds=funds, metrics=metrics), run.days

    own, days = exact([(member.instrument_id, member.weight_pct) for member in members])
    top = sorted(
        (exact(list(zip(ids, map(Decimal, splits[k]), strict=True)))[0] for k in best),
        key=lambda candidate: _better(settings.goal, candidate),
    )

    benchmark = None
    if model.benchmark is not None:
        bench_series = despiked_series(session, model.benchmark, warnings)
        bench_days = engine.replay_flows(bench_series, days) if bench_series else None
        if bench_days is not None:
            benchmark = BenchmarkOut(
                instrument_id=model.benchmark.id,
                name=model.benchmark.name,
                curve=[],
                metrics=_metrics(bench_days, params.risk_free_pct, None),
            )

    began = aligned.dates[aligned.start]
    if params.start and began > params.start:
        youngest = max(ids, key=lambda fund_id: series[fund_id][0][0])
        warnings.append(
            f"Started on {began.isoformat()} instead of {params.start.isoformat()}: "
            f"{names[youngest]} has no NAV before then."
        )
    return OptimiseOut(
        start_date=began,
        end_date=aligned.dates[-1],
        tried=len(splits),
        eligible=int(eligible.sum()),
        points=[
            SearchPoint(
                xirr_pct=engine.figure(xirr),
                max_drawdown_pct=engine.figure(drawdown),
                eligible=bool(ok),
            )
            for xirr, drawdown, ok in zip(
                measures.xirr_pct, measures.max_drawdown_pct, eligible, strict=True
            )
        ],
        model=own,
        benchmark=benchmark,
        top=top,
        warnings=warnings,
    )
