"""The portfolio view: value, P&L, XIRR, allocation and drift (T1-17, D-070, D-071)."""

from datetime import date, datetime
from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

from friday.api.deps import SessionDep
from friday.api.schemas import FundRef
from friday.core.instruments.models import Instrument
from friday.core.navs.service import last_run
from friday.core.portfolio.returns import Returns
from friday.core.portfolio.service import FundPosition, Portfolio, portfolio
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


class PortfolioOut(BaseModel):
    returns: ReturnsOut | None
    """All funds with a NAV together; blank when I hold none."""
    cost: Amount
    realised: Amount
    unrealised: Amount | None
    benchmark_fund: FundRef | None
    benchmark: ReturnsOut | None
    funds: list[FundPositionOut]
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
