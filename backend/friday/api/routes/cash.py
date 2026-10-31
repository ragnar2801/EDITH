"""Cash accounts, the cash plan's settings and the plan itself."""

from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Response
from pydantic import AfterValidator, BaseModel, Field

from friday.api.deps import SessionDep
from friday.api.routes.buckets import ref
from friday.api.routes.models import _sentence
from friday.api.schemas import BucketRef, FundRef, ModelRef
from friday.core.cash.models import CashAccount, PlanSettings
from friday.core.cash.plan import percent
from friday.core.cash.service import (
    CENT,
    AccountInput,
    CashPlan,
    DuplicateAccount,
    Emergency,
    FundValue,
    InvalidCash,
    SettingsInput,
    buy_on_paper,
    cash_plan,
    cash_total,
    create_account,
    delete_account,
    emergency,
    get_settings,
    list_accounts,
    update_account,
    update_settings,
)
from friday.core.instruments.models import Instrument
from friday.core.schema_types import Amount, Nav, Percent, Units, UtcDatetime

router = APIRouter(tags=["cash"])

Rupees = Annotated[Amount, AfterValidator(lambda value: value.quantize(CENT, ROUND_HALF_UP))]
"""An amount shown to the paisa: ``"18000.00"``, not ``"18000"``."""

Earmark = Literal["emergency", "deployable", "reserved"]


class AccountOut(BaseModel):
    id: int
    name: str
    balance: Rupees
    earmark: Earmark
    note: str | None
    updated_at: UtcDatetime


class AccountIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    balance: Amount
    earmark: Earmark
    note: str | None = Field(default=None, max_length=200)


class FundValueOut(BaseModel):
    fund: FundRef
    units: Units
    nav: Nav | None
    nav_date: date | None
    value: Rupees


class EmergencyOut(BaseModel):
    goal: Rupees
    cash: Rupees
    fund: FundValueOut | None
    total: Rupees
    shortfall: Rupees
    """How much the emergency money is below its goal; 0 when it's met."""


class CashOut(BaseModel):
    accounts: list[AccountOut]
    deployable: Rupees
    reserved: Rupees
    emergency: EmergencyOut


class SettingsOut(BaseModel):
    emergency_goal: Rupees
    emergency_fund: FundRef | None
    stagger_fund: FundRef | None
    stagger_threshold: Rupees | None
    """Stagger amounts from this much up; blank: never."""
    stagger_months: int
    min_per_fund: Rupees
    updated_at: UtcDatetime


class SettingsIn(BaseModel):
    emergency_goal: Amount
    emergency_fund_id: int | None = None
    stagger_fund_id: int | None = None
    """The liquid or arbitrage fund staggered money waits in."""
    stagger_threshold: Amount | None = None
    stagger_months: int = Field(ge=2, le=24)
    min_per_fund: Amount


class PlanIn(BaseModel):
    bucket_id: int
    amount: Amount | None = None
    """Blank: all deployable cash (a paper bucket needs an amount)."""


class PaperBuyIn(BaseModel):
    bucket_id: int
    amount: Amount


class PaperBuyOut(BaseModel):
    bucket: BucketRef
    purchases: int
    invested: Rupees


class PlanFundOut(BaseModel):
    fund: FundRef
    weight: Percent
    units: Units
    nav: Nav | None
    nav_date: date | None
    value_now: Rupees
    share_now: Percent | None
    """Share of what the bucket holds of the model's funds now; blank when it holds none."""
    invest: Rupees
    value_after: Rupees
    share_after: Percent | None


class PlanMonthOut(BaseModel):
    month: date
    """First day of the month."""
    total: Rupees
    amounts: list[Rupees]
    """One per fund, in the order of ``funds``."""


class PlanOut(BaseModel):
    amount: Rupees
    bucket: BucketRef
    model: ModelRef
    emergency: EmergencyOut
    emergency_topup: Rupees
    """Kept as emergency money (in the emergency fund, if one is set) before the split."""
    to_funds: Rupees
    """What's left for the split after the emergency top-up."""
    invested: Rupees
    left: Rupees
    """Not invested: paise, or less than the minimum per fund."""
    funds: list[PlanFundOut]
    value_now: Rupees
    value_after: Rupees
    stagger_fund: FundRef | None
    months: list[PlanMonthOut]
    """Monthly transfers when the amount is staggered; empty when it goes in at once."""
    ignored: list[FundValueOut]
    """Funds the bucket holds outside its model: not part of the plan."""
    min_per_fund: Rupees


def _ref(instrument: Instrument) -> FundRef:
    return FundRef.model_validate(instrument, from_attributes=True)


def _account(account: CashAccount) -> AccountOut:
    return AccountOut.model_validate(account, from_attributes=True)


def _value(value: FundValue) -> FundValueOut:
    return FundValueOut(
        fund=_ref(value.instrument),
        units=value.units,
        nav=value.nav,
        nav_date=value.nav_date,
        value=value.value,
    )


def _emergency(status: Emergency) -> EmergencyOut:
    return EmergencyOut(
        goal=status.goal,
        cash=status.cash,
        fund=_value(status.fund) if status.fund else None,
        total=status.total,
        shortfall=status.shortfall,
    )


def _settings(settings: PlanSettings) -> SettingsOut:
    return SettingsOut(
        emergency_goal=settings.emergency_goal,
        emergency_fund=_ref(settings.emergency_fund) if settings.emergency_fund else None,
        stagger_fund=_ref(settings.stagger_fund) if settings.stagger_fund else None,
        stagger_threshold=settings.stagger_threshold,
        stagger_months=settings.stagger_months,
        min_per_fund=settings.min_per_fund,
        updated_at=settings.updated_at,
    )


def _plan(plan: CashPlan) -> PlanOut:
    after = plan.value_now + plan.invested
    funds = [
        PlanFundOut(
            fund=_ref(f.now.instrument),
            weight=f.weight,
            units=f.now.units,
            nav=f.now.nav,
            nav_date=f.now.nav_date,
            value_now=f.now.value,
            share_now=percent(f.now.value, plan.value_now),
            invest=f.invest,
            value_after=f.now.value + f.invest,
            share_after=percent(f.now.value + f.invest, after),
        )
        for f in plan.funds
    ]
    keys = [f.now.instrument.id for f in plan.funds]
    zero = Decimal(0)
    months = [
        PlanMonthOut(
            month=month.start,
            total=sum(month.amounts.values(), zero),
            amounts=[month.amounts.get(key, zero) for key in keys],
        )
        for month in plan.months
    ]
    stagger_fund = plan.settings.stagger_fund
    return PlanOut(
        amount=plan.amount,
        bucket=ref(plan.bucket),
        model=ModelRef(id=plan.model.id, name=plan.model.name),
        emergency=_emergency(plan.emergency),
        emergency_topup=plan.emergency_topup,
        to_funds=plan.amount - plan.emergency_topup,
        invested=plan.invested,
        left=plan.left,
        funds=funds,
        value_now=plan.value_now,
        value_after=after,
        stagger_fund=_ref(stagger_fund) if stagger_fund and months else None,
        months=months,
        ignored=[_value(value) for value in plan.ignored],
        min_per_fund=plan.settings.min_per_fund,
    )


def _do(action, *args):
    try:
        return action(*args)
    except InvalidCash as error:
        raise HTTPException(422, _sentence(error)) from None
    except DuplicateAccount as error:
        raise HTTPException(409, _sentence(error)) from None


def _input(payload: AccountIn) -> AccountInput:
    return AccountInput(
        name=payload.name, balance=payload.balance, earmark=payload.earmark, note=payload.note
    )


def _get(session, account_id: int) -> CashAccount:
    account = session.get(CashAccount, account_id)
    if account is None:
        raise HTTPException(404, f"No cash account with id {account_id}.")
    return account


@router.get("/cash", operation_id="getCash")
def get_cash(session: SessionDep) -> CashOut:
    """My cash accounts, totals per earmark, and the emergency money against its goal."""
    return CashOut(
        accounts=[_account(account) for account in list_accounts(session)],
        deployable=cash_total(session, "deployable"),
        reserved=cash_total(session, "reserved"),
        emergency=_emergency(_do(emergency, session)),
    )


@router.post("/cash/accounts", status_code=201, operation_id="addCashAccount")
def add_account(session: SessionDep, payload: AccountIn) -> AccountOut:
    return _account(_do(create_account, session, _input(payload)))


@router.put("/cash/accounts/{account_id}", operation_id="updateCashAccount")
def change_account(session: SessionDep, account_id: int, payload: AccountIn) -> AccountOut:
    return _account(_do(update_account, session, _get(session, account_id), _input(payload)))


@router.delete("/cash/accounts/{account_id}", status_code=204, operation_id="deleteCashAccount")
def remove_account(session: SessionDep, account_id: int) -> Response:
    delete_account(session, _get(session, account_id))
    return Response(status_code=204)


@router.get("/plan/settings", operation_id="getPlanSettings")
def read_settings(session: SessionDep) -> SettingsOut:
    """Emergency goal and fund, the minimum per fund and the staggering rule."""
    return _settings(get_settings(session))


@router.put("/plan/settings", operation_id="updatePlanSettings")
def change_settings(session: SessionDep, payload: SettingsIn) -> SettingsOut:
    data = SettingsInput(
        emergency_goal=payload.emergency_goal,
        emergency_fund_id=payload.emergency_fund_id,
        stagger_fund_id=payload.stagger_fund_id,
        stagger_threshold=payload.stagger_threshold,
        stagger_months=payload.stagger_months,
        min_per_fund=payload.min_per_fund,
    )
    return _settings(_do(update_settings, session, data))


@router.post("/plan", operation_id="makeCashPlan")
def make(session: SessionDep, payload: PlanIn) -> PlanOut:
    """Where new cash should go in a bucket: emergency top-up first (real buckets), then the
    funds of its model furthest below their weights, never selling. Large amounts in a real
    bucket come with a monthly stagger plan. Nothing is saved."""
    return _plan(_do(cash_plan, session, payload.bucket_id, payload.amount))


@router.post("/plan/paper", status_code=201, operation_id="buyPlanOnPaper")
def buy_paper(session: SessionDep, payload: PaperBuyIn) -> PaperBuyOut:
    """Buy a paper bucket's plan for the amount: one purchase per fund that gets money, at
    its latest NAV."""
    lots = _do(buy_on_paper, session, payload.bucket_id, payload.amount)
    return PaperBuyOut(
        bucket=ref(lots[0].bucket),
        purchases=len(lots),
        invested=sum((lot.amount for lot in lots), Decimal(0)),
    )
