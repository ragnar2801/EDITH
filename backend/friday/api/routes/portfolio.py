"""The portfolio view: value, P&L, XIRR, allocation and drift; the
day's move, the gap to the benchmark, SIPs and value over time."""

from datetime import date, datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Query
from pydantic import BaseModel

from friday.api.deps import SessionDep
from friday.api.schemas import FundRef
from friday.core.instruments.models import Instrument
from friday.core.navs.service import last_run
from friday.core.portfolio.history import Change, Point
from friday.core.portfolio.returns import Returns
from friday.core.portfolio.service import FundPosition, Portfolio, history, portfolio
from friday.core.schema_types import Amount, Nav, Percent, Units, UtcDatetime

router = APIRouter(tags=["portfolio"])


class ReturnsOut(BaseModel):
    invested: Amount
    """Every rupee put in."""
    redeemed: Amount
    """Every rupee taken out by selling."""
    value: Amount
    """What is still held is worth at the latest NAV."""
    gain: Amount
    """Value + redeemed − invested: realised and unrealised P&L together."""
    return_pct: Percent | None
    """Gain ÷ invested."""
    xirr_pct: Percent | None
    """Annual money-weighted return; blank until the first money has been in a year."""
    since: date | None
    on: date
    """The NAV date the value is at."""


class ChangeOut(BaseModel):
    start: date
    """The date the change is measured from."""
    end: date
    gain: Amount
    """Value at the end − value at the start − money put in between."""
    return_pct: Percent | None
    """Time-weighted return between the two dates."""


class FundPositionOut(BaseModel):
    fund: FundRef
    role: Literal["target", "emergency", "outside"]
    units: Units
    cost: Amount
    """What the units still held cost."""
    realised: Amount
    unrealised: Amount | None
    nav: Nav | None
    nav_date: date | None
    share: Percent | None
    """Share of what all my funds are worth."""
    returns: ReturnsOut | None
    """Blank when Friday has no NAV for the fund: sync NAVs."""
    benchmark: ReturnsOut | None
    """The same money on the same dates in the benchmark fund."""
    ahead: Amount | None
    """Gain − the benchmark's gain: rupees ahead of (or, below 0, behind) the benchmark."""
    day: ChangeOut | None
    """The move between the fund's last two NAVs, less money put in."""


class AssetOut(BaseModel):
    asset: Literal["equity", "debt", "gold", "silver", "other", "unclassified"]
    value: Amount
    share: Percent | None


class DriftOut(BaseModel):
    fund: FundRef
    weight: Percent
    value: Amount
    share: Percent | None
    """Share of what I hold of the target split's funds."""
    drift: Percent | None
    """Share − weight, in percentage points: below 0 is under target."""


class TargetOut(BaseModel):
    id: int
    name: str


class CashTotalsOut(BaseModel):
    deployable: Amount
    emergency: Amount
    reserved: Amount
    total: Amount


class SipsOut(BaseModel):
    monthly: Amount
    """Every active SIP's amount together."""
    count: int
    next_date: date | None
    next_fund: FundRef | None


class PortfolioOut(BaseModel):
    returns: ReturnsOut | None
    """All funds with a NAV together; blank when I hold none."""
    cost: Amount
    realised: Amount
    unrealised: Amount | None
    benchmark_fund: FundRef | None
    benchmark: ReturnsOut | None
    ahead: Amount | None
    """Gain − the benchmark's gain on the same flows."""
    day: ChangeOut | None
    """The funds' day moves added up, from the earliest previous NAV date to the latest."""
    sips: SipsOut
    funds: list[FundPositionOut]
    """Biggest first; funds without a NAV last."""
    allocation: list[AssetOut]
    target: TargetOut | None
    drift: list[DriftOut]
    cash: CashTotalsOut
    net_worth: Amount
    """Funds plus every cash account."""
    missing_nav: list[FundRef]
    nav_oldest: date | None
    """The oldest of the held funds' latest NAV dates."""
    nav_newest: date | None
    last_sync: UtcDatetime | None


class HistoryPointOut(BaseModel):
    date: date
    value: Amount
    invested: Amount
    """What the units held on the date cost."""
    benchmark: Amount | None
    """The same money in the benchmark fund."""


class HistoryOut(BaseModel):
    benchmark_fund: FundRef | None
    points: list[HistoryPointOut]
    """Every NAV date from the start, or the last date of each week or month over long
    ranges (for drawing only)."""
    change: ChangeOut | None
    """Over the range, worked out on every date."""
    benchmark_change: ChangeOut | None


def _ref(instrument: Instrument) -> FundRef:
    return FundRef.model_validate(instrument, from_attributes=True)


def _returns(value: Returns | None) -> ReturnsOut | None:
    if value is None:
        return None
    return ReturnsOut(
        invested=value.invested,
        redeemed=value.redeemed,
        value=value.value,
        gain=value.gain,
        return_pct=value.return_pct,
        xirr_pct=value.xirr_pct,
        since=value.since,
        on=value.on,
    )


def _change(value: Change | None) -> ChangeOut | None:
    if value is None:
        return None
    return ChangeOut(start=value.start, end=value.end, gain=value.gain, return_pct=value.return_pct)


def _fund(view: Portfolio, fund: FundPosition) -> FundPositionOut:
    return FundPositionOut(
        fund=_ref(fund.instrument),
        role=fund.role,
        units=fund.units,
        cost=fund.cost,
        realised=fund.realised,
        unrealised=fund.unrealised,
        nav=fund.nav,
        nav_date=fund.nav_date,
        share=view.share(fund),
        returns=_returns(fund.returns),
        benchmark=_returns(fund.benchmark),
        ahead=fund.ahead,
        day=_change(fund.day),
    )


@router.get("/portfolio", operation_id="getPortfolio")
def get_portfolio(session: SessionDep) -> PortfolioOut:
    view = portfolio(session)
    run = last_run(session)
    finished: datetime | None = run.finished_at if run else None
    dates = view.nav_dates
    return PortfolioOut(
        returns=_returns(view.returns),
        cost=view.cost,
        realised=view.realised,
        unrealised=view.unrealised,
        benchmark_fund=_ref(view.benchmark_fund) if view.benchmark_fund else None,
        benchmark=_returns(view.benchmark),
        ahead=view.ahead,
        day=_change(view.day),
        sips=SipsOut(
            monthly=view.sips.monthly,
            count=view.sips.count,
            next_date=view.sips.next_date,
            next_fund=_ref(view.sips.next_fund) if view.sips.next_fund else None,
        ),
        funds=[_fund(view, fund) for fund in view.funds],
        allocation=[AssetOut(asset=s.asset, value=s.value, share=s.share) for s in view.allocation],
        target=TargetOut(id=view.target.id, name=view.target.name) if view.target else None,
        drift=[
            DriftOut(
                fund=_ref(row.instrument),
                weight=row.weight,
                value=row.value,
                share=row.share,
                drift=row.drift,
            )
            for row in view.drift
        ],
        cash=CashTotalsOut(**view.cash, total=view.cash_total),
        net_worth=view.net_worth,
        missing_nav=[_ref(i) for i in view.missing_nav],
        nav_oldest=dates[0] if dates else None,
        nav_newest=dates[1] if dates else None,
        last_sync=finished,
    )


@router.get("/portfolio/history", operation_id="getPortfolioHistory")
def get_portfolio_history(
    session: SessionDep, start: Annotated[date | None, Query()] = None
) -> HistoryOut:
    """Value, invested and the benchmark over time, from ``start`` (or the first purchase)
    to the latest NAV date, with the gain and return over that range."""
    view = history(session, start)
    bench: dict[date, Point] = {p.date: p for p in view.benchmark or []}
    return HistoryOut(
        benchmark_fund=_ref(view.benchmark_fund) if view.benchmark_fund else None,
        points=[
            HistoryPointOut(
                date=p.date,
                value=p.value,
                invested=p.cost,
                benchmark=bench[p.date].value if p.date in bench else None,
            )
            for p in view.points
        ],
        change=_change(view.change),
        benchmark_change=_change(view.benchmark_change),
    )
