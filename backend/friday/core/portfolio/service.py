"""The portfolio view: what my funds are worth, what they made, how they did against the
same money in the benchmark fund, how they moved on the last NAV date, how they split over
asset classes, and the same over time.

The view is of real money (purchases in no bucket or a real one) or of one bucket. A
bucket with a model also shows how far each of the model's funds is from its weight, and
the same money split by the model's weights on the same dates.

Every figure is worked out here; the UI only shows them.
"""

from dataclasses import dataclass, replace
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from friday.core.buckets.models import Bucket
from friday.core.cash.service import cash_total, get_settings
from friday.core.holdings.models import Lot
from friday.core.holdings.service import (
    Holding,
    list_holdings,
    next_due,
    sip_active,
    sold_cost,
    today,
)
from friday.core.instruments.models import ASSETS, Instrument
from friday.core.instruments.service import effective_classification
from friday.core.models.models import Model
from friday.core.models.service import default_benchmark
from friday.core.navs.models import FundNav
from friday.core.navs.service import nav_series
from friday.core.portfolio.history import (
    Change,
    Move,
    Point,
    change,
    combine,
    daily,
    mirror,
    replay,
    replay_split,
    thin,
)
from friday.core.portfolio.returns import ZERO, Flow, Returns, money, pct, returns

UNCLASSIFIED = "unclassified"
EARMARKS = ("deployable", "emergency", "reserved")


@dataclass(frozen=True)
class FundPosition:
    instrument: Instrument
    role: str
    """``target`` (in the bucket's model), ``emergency`` (the emergency fund) or ``outside``."""
    units: Decimal
    cost: Decimal
    """What the units still held cost."""
    realised: Decimal
    """Sale proceeds minus what the units sold cost."""
    nav: Decimal | None
    nav_date: date | None
    returns: Returns | None
    """``None`` when Friday has no NAV for the fund yet."""
    benchmark: Returns | None
    lots: list[Lot]
    day: Change | None = None
    """The move between the fund's last two NAVs, less money put in."""

    @property
    def value(self) -> Decimal | None:
        return self.returns.value if self.returns else None

    @property
    def ahead(self) -> Decimal | None:
        """Rupees gained beyond the same money in the benchmark; below 0 is behind."""
        return ahead(self.returns, self.benchmark)

    @property
    def unrealised(self) -> Decimal | None:
        """Gain minus realised, so the two always add up to the gain to the paisa."""
        return self.returns.gain - self.realised if self.returns else None


@dataclass(frozen=True)
class AssetSlice:
    asset: str
    value: Decimal
    share: Decimal | None


@dataclass(frozen=True)
class Drift:
    instrument: Instrument
    weight: Decimal
    value: Decimal
    share: Decimal | None
    """Share of what the bucket holds of the model's funds, in percent."""
    drift: Decimal | None
    """``share - weight``, in percentage points: below 0 is under target."""


@dataclass(frozen=True)
class Sips:
    monthly: Decimal
    """Every active SIP's amount together."""
    count: int
    next_date: date | None
    next_fund: Instrument | None


@dataclass(frozen=True)
class Portfolio:
    funds: list[FundPosition]
    returns: Returns | None
    """All funds with a NAV together; ``None`` when there are none."""
    realised: Decimal
    cost: Decimal
    benchmark_fund: Instrument | None
    benchmark: Returns | None
    allocation: list[AssetSlice]
    bucket: Bucket | None
    model: Model | None
    """The bucket's model."""
    model_returns: Returns | None
    """The same flows split by the model's weights."""
    drift: list[Drift]
    cash: dict[str, Decimal]
    day: Change | None
    """The funds' day moves added up: from the earliest of their previous NAV dates
    to the latest of their last ones."""
    sips: Sips

    @property
    def ahead(self) -> Decimal | None:
        return ahead(self.returns, self.benchmark)

    @property
    def ahead_of_model(self) -> Decimal | None:
        return ahead(self.returns, self.model_returns)

    @property
    def nav_dates(self) -> tuple[date, date] | None:
        """Oldest and newest of the held funds' latest NAV dates: apart means a sync is due."""
        dates = [f.nav_date for f in self.funds if f.nav_date and f.units > 0]
        return (min(dates), max(dates)) if dates else None

    def share(self, fund: FundPosition) -> Decimal | None:
        """The fund's share of what all my funds are worth, in percent."""
        if fund.value is None or self.returns is None:
            return None
        return pct(fund.value, self.returns.value)

    @property
    def cash_total(self) -> Decimal:
        return money(sum(self.cash.values(), ZERO))

    @property
    def net_worth(self) -> Decimal:
        """Funds with a NAV plus every cash account, earmarked or not."""
        return money((self.returns.value if self.returns else ZERO) + self.cash_total)

    @property
    def missing_nav(self) -> list[Instrument]:
        return [f.instrument for f in self.funds if f.returns is None]

    @property
    def unrealised(self) -> Decimal | None:
        return self.returns.gain - self.realised if self.returns else None


def ahead(mine: Returns | None, benchmark: Returns | None) -> Decimal | None:
    """Gain less the benchmark's gain on the same flows."""
    return mine.gain - benchmark.gain if mine and benchmark else None


def _moves(lots: list[Lot]) -> list[Move]:
    """Every buy and sale of a fund's lots as moves, with the proceeds of a sale
    rounded to the paisa as in :func:`_flows`."""
    moves = []
    for lot in lots:
        if lot.skipped:
            continue
        moves.append(Move(lot.buy_date, lot.units, lot.amount, lot.amount, lot.nav))
        for sale in lot.sales:
            proceeds = money(sale.units * sale.nav)
            moves.append(Move(sale.sale_date, -sale.units, -sold_cost(sale), -proceeds, sale.nav))
    return moves


def _last_navs(session: Session, instrument_id: int, count: int) -> list[tuple[date, Decimal]]:
    """The fund's last ``count`` stored NAVs, oldest first."""
    rows = session.execute(
        select(FundNav.nav_date, FundNav.nav)
        .where(FundNav.instrument_id == instrument_id)
        .order_by(FundNav.nav_date.desc())
        .limit(count)
    ).all()
    return [(row[0], row[1]) for row in reversed(rows)]


def _flows(lots: list[Lot]) -> tuple[list[Flow], Decimal]:
    """Cash flows of a fund's lots, and the P&L its sales realised (exact)."""
    flows, realised = [], ZERO
    for lot in lots:
        if lot.skipped:
            continue
        flows.append(Flow(lot.buy_date, lot.amount))
        for sale in lot.sales:
            proceeds = money(sale.units * sale.nav)
            flows.append(Flow(sale.sale_date, -proceeds))
            realised += proceeds - sold_cost(sale)
    return flows, realised


def _position(
    held: Holding,
    role: str,
    last: list[tuple[date, Decimal]],
    benchmark: list[tuple[date, Decimal]] | None,
) -> FundPosition:
    flows, realised = _flows(held.lots)
    latest = last[-1] if last else None
    nav_date, nav = latest if latest else (None, None)
    result = mirror = None
    if latest:
        result = returns(flows, money(held.units * nav), nav_date)
        if benchmark:
            mirror = replay(benchmark, flows, nav_date)
    return FundPosition(
        instrument=held.instrument,
        role=role,
        units=held.units,
        cost=held.cost,
        realised=money(realised),
        nav=nav,
        nav_date=nav_date,
        returns=result,
        benchmark=mirror,
        lots=held.lots,
    )


def _allocation(funds: list[FundPosition]) -> list[AssetSlice]:
    """Fund values split over asset classes by each fund's classification."""
    amounts: dict[str, Decimal] = {}
    for fund in funds:
        if not fund.value:
            continue
        split = effective_classification(fund.instrument).allocation or {UNCLASSIFIED: Decimal(100)}
        for asset, share in split.items():
            amounts[asset] = amounts.get(asset, ZERO) + fund.value * share / 100
    total = sum(amounts.values(), ZERO)
    return [
        AssetSlice(asset, money(amounts[asset]), pct(amounts[asset], total))
        for asset in (*ASSETS, UNCLASSIFIED)
        if amounts.get(asset)
    ]


def _drift(model: Model, funds: list[FundPosition]) -> list[Drift]:
    values = {f.instrument.id: f.value or ZERO for f in funds}
    total = sum((values.get(m.instrument_id, ZERO) for m in model.funds), ZERO)
    rows = []
    for member in model.funds:
        value = values.get(member.instrument_id, ZERO)
        share = pct(value, total)
        weight = money(member.weight_pct)
        drift = share - weight if share is not None else None
        rows.append(Drift(member.instrument, weight, money(value), share, drift))
    return rows


def _day(funds: list[FundPosition], navs: dict[int, list[tuple[date, Decimal]]]):
    """Each fund's move between its own last two NAVs, less money put in, and the
    moves added up.

    Each fund uses its own dates because funds publish on different days: liquid funds
    have NAVs at weekends, equity funds don't. The total's return is its gain over what
    the funds were worth on their previous NAV dates."""
    moved, gains, base, starts, ends = [], [], ZERO, [], []
    for fund in funds:
        last = navs[fund.instrument.id]
        if len(last) < 2:
            moved.append(fund)
            continue
        pair = [day for day, _ in last]
        line = daily(_moves(fund.lots), last, pair)
        day = change(line, pair[0])
        moved.append(replace(fund, day=day))
        if day:
            gains.append(day.gain)
            base += line[0].value
            starts.append(pair[0])
            ends.append(pair[1])
    if not gains:
        return moved, None
    gain = money(sum(gains, ZERO))
    rate = pct(gain, base) if base > 0 else None
    return moved, Change(min(starts), max(ends), gain, rate)


def _sips(holdings: list[Holding]) -> Sips:
    active = [sip for held in holdings for sip in held.sips if sip_active(sip)]
    upcoming = [(due, sip) for sip in active if (due := next_due(sip, today()))]
    first = min(upcoming, key=lambda pair: (pair[0], pair[1].id), default=None)
    return Sips(
        monthly=money(sum((sip.amount for sip in active), ZERO)),
        count=len(active),
        next_date=first[0] if first else None,
        next_fund=first[1].instrument if first else None,
    )


def _sort_key(fund: FundPosition):
    """Biggest first; funds without a NAV last."""
    return (fund.value is None, -(fund.value or ZERO), fund.instrument.name)


def _benchmark(session: Session, model: Model | None) -> Instrument | None:
    return (model.benchmark if model else None) or default_benchmark(session)


def _model_returns(session: Session, model: Model, flows: list[Flow], on: date) -> Returns | None:
    split = [(m.weight_pct, nav_series(session, m.instrument_id)) for m in model.funds]
    if not flows or not all(series for _, series in split):
        return None
    return replay_split(split, flows, on)


def portfolio(session: Session, bucket: Bucket | None = None) -> Portfolio:
    """Real money, or one bucket's."""
    settings = get_settings(session)
    model = bucket.model if bucket else None
    in_model = {m.instrument_id for m in model.funds} if model else set()
    emergency_id = None if bucket and bucket.paper else settings.emergency_fund_id
    benchmark_fund = _benchmark(session, model)
    series = nav_series(session, benchmark_fund.id) if benchmark_fund else None

    funds, navs = [], {}
    holdings = list_holdings(session, bucket.id if bucket else None)
    for held in holdings:
        if not any(not lot.skipped for lot in held.lots):
            continue  # a SIP with no instalment yet
        role = (
            "target"
            if held.instrument.id in in_model
            else "emergency"
            if held.instrument.id == emergency_id
            else "outside"
        )
        navs[held.instrument.id] = _last_navs(session, held.instrument.id, 2)
        funds.append(_position(held, role, navs[held.instrument.id], series))

    priced, day = _day([f for f in funds if f.returns], navs)
    funds = sorted([*priced, *(f for f in funds if f.returns is None)], key=_sort_key)
    overall = same = split = None
    if priced:
        on = max(f.returns.on for f in priced)
        flows = [flow for f in priced for flow in _flows(f.lots)[0]]
        overall = returns(flows, sum((f.value for f in priced), ZERO), on)
        if series:
            same = replay(series, flows, on)
        if model:
            split = _model_returns(session, model, flows, on)
    return Portfolio(
        funds=funds,
        returns=overall,
        realised=money(sum((f.realised for f in priced), ZERO)),
        cost=money(sum((f.cost for f in funds), ZERO)),
        benchmark_fund=benchmark_fund if series else None,
        benchmark=same,
        allocation=_allocation(priced),
        bucket=bucket,
        model=model,
        model_returns=split,
        drift=_drift(model, funds) if model else [],
        cash={earmark: money(cash_total(session, earmark)) for earmark in EARMARKS},
        day=day,
        sips=_sips(holdings),
    )


@dataclass(frozen=True)
class History:
    points: list[Point]
    """What is drawn: value and cost of every fund with a NAV (thinned)."""
    benchmark: list[Point] | None
    """The same money in the benchmark, on the same dates."""
    benchmark_fund: Instrument | None
    change: Change | None
    """Gain and time-weighted return over the range, worked out on every date."""
    benchmark_change: Change | None


def history(session: Session, start: date | None = None, bucket: Bucket | None = None) -> History:
    """Value, cost and the benchmark's value on every NAV date from the first purchase (or
    the last date on or before ``start``) to the latest NAV date, of real money or one
    bucket. Funds without a stored NAV are left out, as in the totals."""
    benchmark_fund = _benchmark(session, bucket.model if bucket else None)
    held = []
    for holding in list_holdings(session, bucket.id if bucket else None):
        series = nav_series(session, holding.instrument.id)
        moves = _moves(holding.lots)
        if series and moves:
            held.append((moves, series))
    if not held:
        return History([], None, benchmark_fund, None, None)

    on = max(series[-1][0] for _, series in held)
    first = min(move.date for moves, _ in held for move in moves)
    dates = sorted(
        {day for _, series in held for day, _ in series if first <= day <= on}
        | {move.date for moves, _ in held for move in moves if move.date <= on}
    )
    points = combine([daily(moves, series, dates) for moves, series in held])

    bench = None
    if benchmark_fund:
        index = nav_series(session, benchmark_fund.id)
        flows = [Flow(move.date, move.flow) for moves, _ in held for move in moves]
        copied = mirror(index, flows) if index else None
        if copied is not None:
            bench = daily(copied, index, dates)

    def shown(line: list[Point]) -> list[Point]:
        if start is None:
            return thin(line)
        base = max((i for i, p in enumerate(line) if p.date <= start), default=0)
        return thin(line[base:])

    return History(
        points=shown(points),
        benchmark=shown(bench) if bench else None,
        benchmark_fund=benchmark_fund if bench else None,
        change=change(points, start),
        benchmark_change=change(bench, start) if bench else None,
    )
