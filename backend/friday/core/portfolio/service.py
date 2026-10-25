"""The portfolio view (T1-17, D-070, D-071): what my funds are worth, what they made, how
they did against the same money in the Nifty 50 index fund, how they split over asset
classes and how far each is from my target split.

Every figure is worked out here; the UI only shows them (D-032).
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from friday.core.buckets.models import Bucket
from friday.core.buckets.service import default_benchmark
from friday.core.cash.service import cash_total, get_settings, latest_nav
from friday.core.holdings.models import Lot
from friday.core.holdings.service import Holding, list_holdings, sold_cost
from friday.core.instruments.models import BUCKETS, Instrument
from friday.core.instruments.service import effective_classification
from friday.core.navs.service import nav_series
from friday.core.portfolio.returns import ZERO, Flow, Returns, money, pct, replay, returns

UNCLASSIFIED = "unclassified"
EARMARKS = ("deployable", "emergency", "reserved")


@dataclass(frozen=True)
class FundPosition:
    instrument: Instrument
    role: str
    """``target`` (in my target split), ``emergency`` (the emergency fund) or ``outside``."""
    units: Decimal
    cost: Decimal
    """What the units still held cost (T1-15)."""
    realised: Decimal
    """Sale proceeds minus what the units sold cost."""
    nav: Decimal | None
    nav_date: date | None
    returns: Returns | None
    """``None`` when Friday has no NAV for the fund yet."""
    benchmark: Returns | None
    lots: list[Lot]

    @property
    def value(self) -> Decimal | None:
        return self.returns.value if self.returns else None

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
    """Share of what I hold of the target split's funds, in percent."""
    drift: Decimal | None
    """``share - weight``, in percentage points: below 0 is under target."""


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
    target: Bucket | None
    drift: list[Drift]
    cash: dict[str, Decimal]

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
    session: Session, held: Holding, role: str, benchmark: list[tuple[date, Decimal]] | None
) -> FundPosition:
    flows, realised = _flows(held.lots)
    latest = latest_nav(session, held.instrument.id)
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
    """Fund values split over asset classes by each fund's classification (D-040)."""
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
        for asset in (*BUCKETS, UNCLASSIFIED)
        if amounts.get(asset)
    ]


def _drift(bucket: Bucket, funds: list[FundPosition]) -> list[Drift]:
    values = {f.instrument.id: f.value or ZERO for f in funds}
    total = sum((values.get(m.instrument_id, ZERO) for m in bucket.funds), ZERO)
    rows = []
    for member in bucket.funds:
        value = values.get(member.instrument_id, ZERO)
        share = pct(value, total)
        weight = money(member.weight_pct)
        drift = share - weight if share is not None else None
        rows.append(Drift(member.instrument, weight, money(value), share, drift))
    return rows


def portfolio(session: Session) -> Portfolio:
    settings = get_settings(session)
    target = settings.target_bucket
    in_target = {m.instrument_id for m in target.funds} if target else set()
    benchmark_fund = (target.benchmark if target else None) or default_benchmark(session)
    series = nav_series(session, benchmark_fund.id) if benchmark_fund else None

    funds = []
    for held in list_holdings(session):
        if not any(not lot.skipped for lot in held.lots):
            continue  # a SIP with no instalment yet
        role = (
            "target"
            if held.instrument.id in in_target
            else "emergency"
            if held.instrument.id == settings.emergency_fund_id
            else "outside"
        )
        funds.append(_position(session, held, role, series))

    priced = [f for f in funds if f.returns]
    overall = mirror = None
    if priced:
        on = max(f.returns.on for f in priced)
        flows = [flow for f in priced for flow in _flows(f.lots)[0]]
        overall = returns(flows, sum((f.value for f in priced), ZERO), on)
        if series:
            mirror = replay(series, flows, on)
    return Portfolio(
        funds=funds,
        returns=overall,
        realised=money(sum((f.realised for f in priced), ZERO)),
        cost=money(sum((f.cost for f in funds), ZERO)),
        benchmark_fund=benchmark_fund if series else None,
        benchmark=mirror,
        allocation=_allocation(priced),
        target=target,
        drift=_drift(target, funds) if target else [],
        cash={earmark: money(cash_total(session, earmark)) for earmark in EARMARKS},
    )
