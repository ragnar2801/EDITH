"""Cash accounts, the plan's settings, and the cash plan for a bucket.

The plan moves a bucket towards its model, counting only what the bucket holds. Emergency
money is the emergency-earmarked cash plus what I hold of the emergency fund outside paper
buckets. It is never part of a plan: a real bucket's plan only tops it up to the goal. A
paper bucket's plan uses the amount asked for, goes in at once, and can be bought on paper
at each fund's latest NAV. A fund's value is its units held × its latest stored NAV.
"""

from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from friday.core.buckets.models import Bucket
from friday.core.cash.models import EARMARKS, CashAccount, PlanSettings
from friday.core.cash.plan import Month, Target, make_plan
from friday.core.holdings.models import Lot
from friday.core.holdings.service import (
    BuyInput,
    InvalidHolding,
    Scope,
    create_lump_sum,
    held_ids,
    holding,
    today,
)
from friday.core.instruments.models import Instrument
from friday.core.models.models import Model
from friday.core.navs.models import FundNav

ZERO = Decimal(0)
CENT = Decimal("0.01")

DEFAULT_STAGGER_FROM = Decimal(500_000)
DEFAULT_STAGGER_MONTHS = 6
DEFAULT_MIN_PER_FUND = Decimal(500)
MONTHS = range(2, 25)


class InvalidCash(ValueError):
    pass


class DuplicateAccount(ValueError):
    pass


def _now() -> datetime:
    return datetime.now(UTC)


def _note(text: str | None) -> str | None:
    return (text or "").strip() or None


# Accounts ---------------------------------------------------------------------------------


@dataclass(frozen=True)
class AccountInput:
    name: str
    balance: Decimal
    earmark: str
    note: str | None = None


def _validate_account(session: Session, data: AccountInput, account_id: int | None) -> str:
    name = " ".join(data.name.split())
    if not name:
        raise InvalidCash("give the account a name")
    if data.balance < 0:
        raise InvalidCash("the balance can't be below 0")
    if data.earmark not in EARMARKS:
        raise InvalidCash(f"the earmark must be one of {', '.join(EARMARKS)}")
    clash = session.scalars(select(CashAccount).where(CashAccount.name == name)).first()
    if clash is not None and clash.id != account_id:
        raise DuplicateAccount(f"there is already an account called {name}")
    return name


def _apply(account: CashAccount, data: AccountInput, name: str) -> None:
    account.name = name
    account.balance = data.balance
    account.earmark = data.earmark
    account.note = _note(data.note)
    account.updated_at = _now()


def create_account(session: Session, data: AccountInput) -> CashAccount:
    name = _validate_account(session, data, None)
    account = CashAccount(created_at=_now())
    _apply(account, data, name)
    session.add(account)
    session.flush()
    return account


def update_account(session: Session, account: CashAccount, data: AccountInput) -> CashAccount:
    _apply(account, data, _validate_account(session, data, account.id))
    session.flush()
    return account


def delete_account(session: Session, account: CashAccount) -> None:
    session.delete(account)
    session.flush()


def list_accounts(session: Session) -> list[CashAccount]:
    return list(session.scalars(select(CashAccount).order_by(CashAccount.name)))


def cash_total(session: Session, earmark: str) -> Decimal:
    return sum((a.balance for a in list_accounts(session) if a.earmark == earmark), ZERO)


# Settings ---------------------------------------------------------------------------------


@dataclass(frozen=True)
class SettingsInput:
    emergency_goal: Decimal
    emergency_fund_id: int | None
    stagger_fund_id: int | None
    stagger_threshold: Decimal | None
    stagger_months: int
    min_per_fund: Decimal


def get_settings(session: Session) -> PlanSettings:
    """The settings row, made with the defaults the first time it's asked for."""
    settings = session.get(PlanSettings, 1)
    if settings is None:
        settings = PlanSettings(
            id=1,
            emergency_goal=ZERO,
            stagger_threshold=DEFAULT_STAGGER_FROM,
            stagger_months=DEFAULT_STAGGER_MONTHS,
            min_per_fund=DEFAULT_MIN_PER_FUND,
            updated_at=_now(),
        )
        session.add(settings)
        session.flush()
    return settings


def _fund(session: Session, instrument_id: int, role: str) -> Instrument:
    instrument = session.get(Instrument, instrument_id)
    if instrument is None:
        raise InvalidCash(f"{role}: no instrument with id {instrument_id}")
    if not instrument.amfi_code:
        raise InvalidCash(f"{role}: {instrument.name} is not a mutual fund scheme")
    return instrument


def _check_emergency_fund(model: Model, fund: Instrument | None) -> None:
    if fund is None:
        return
    if any(member.instrument_id == fund.id for member in model.funds):
        raise InvalidCash(
            f"the emergency fund {fund.name} is in the model {model.name}; "
            "emergency money can't be part of the split"
        )


def update_settings(session: Session, data: SettingsInput) -> PlanSettings:
    if data.emergency_fund_id is not None:
        _fund(session, data.emergency_fund_id, "emergency fund")
    if data.stagger_fund_id is not None:
        _fund(session, data.stagger_fund_id, "stagger fund")
    if data.emergency_goal < 0:
        raise InvalidCash("the emergency goal can't be below 0")
    if data.stagger_threshold is not None and data.stagger_threshold <= 0:
        raise InvalidCash("the stagger threshold must be more than 0, or blank for never")
    if data.stagger_months not in MONTHS:
        raise InvalidCash(f"stagger over {MONTHS.start} to {MONTHS.stop - 1} months")
    if data.min_per_fund < 0:
        raise InvalidCash("the minimum per fund can't be below 0")

    settings = get_settings(session)
    settings.emergency_goal = data.emergency_goal
    settings.emergency_fund_id = data.emergency_fund_id
    settings.stagger_fund_id = data.stagger_fund_id
    settings.stagger_threshold = data.stagger_threshold
    settings.stagger_months = data.stagger_months
    settings.min_per_fund = data.min_per_fund
    settings.updated_at = _now()
    session.flush()
    session.refresh(settings)
    return settings


# Values -----------------------------------------------------------------------------------


@dataclass(frozen=True)
class FundValue:
    instrument: Instrument
    units: Decimal
    nav: Decimal | None
    nav_date: date | None
    value: Decimal


def latest_nav(session: Session, instrument_id: int) -> tuple[date, Decimal] | None:
    row = session.execute(
        select(FundNav.nav_date, FundNav.nav)
        .where(FundNav.instrument_id == instrument_id)
        .order_by(FundNav.nav_date.desc())
        .limit(1)
    ).first()
    return (row[0], row[1]) if row else None


def fund_value(session: Session, instrument: Instrument, scope: Scope = None) -> FundValue:
    """What I hold of a fund (in ``scope``) at its latest stored NAV. Holding nothing is worth
    0 even without NAVs; holding units without a NAV is refused."""
    units = holding(session, instrument, scope).units
    latest = latest_nav(session, instrument.id)
    if latest is None:
        if units:
            raise InvalidCash(f"Friday has no NAV for {instrument.name}; sync NAVs first")
        return FundValue(instrument, units, None, None, ZERO)
    nav_date, nav = latest
    value = (units * nav).quantize(CENT, ROUND_HALF_UP)
    return FundValue(instrument, units, nav, nav_date, value)


@dataclass(frozen=True)
class Emergency:
    goal: Decimal
    cash: Decimal
    """Emergency-earmarked cash."""
    fund: FundValue | None
    """What I hold of the emergency fund."""

    @property
    def total(self) -> Decimal:
        return self.cash + (self.fund.value if self.fund else ZERO)

    @property
    def shortfall(self) -> Decimal:
        return max(self.goal - self.total, ZERO)


def emergency(session: Session) -> Emergency:
    settings = get_settings(session)
    fund = settings.emergency_fund
    return Emergency(
        goal=settings.emergency_goal,
        cash=cash_total(session, "emergency"),
        fund=fund_value(session, fund) if fund else None,
    )


# The plan ---------------------------------------------------------------------------------


@dataclass(frozen=True)
class FundPlan:
    now: FundValue
    weight: Decimal
    invest: Decimal


@dataclass(frozen=True)
class CashPlan:
    amount: Decimal
    bucket: Bucket
    model: Model
    emergency: Emergency
    emergency_topup: Decimal
    funds: list[FundPlan]
    left: Decimal
    months: list[Month]
    ignored: list[FundValue]
    """Funds the bucket holds outside its model (and not the emergency fund): left out."""
    settings: PlanSettings

    @property
    def value_now(self) -> Decimal:
        return sum((f.now.value for f in self.funds), ZERO)

    @property
    def invested(self) -> Decimal:
        return sum((f.invest for f in self.funds), ZERO)


def _bucket(session: Session, bucket_id: int) -> Bucket:
    bucket = session.get(Bucket, bucket_id)
    if bucket is None:
        raise InvalidCash(f"no bucket with id {bucket_id}")
    return bucket


def cash_plan(session: Session, bucket_id: int, amount: Decimal | None = None) -> CashPlan:
    """Where ``amount`` should go in the bucket (blank: all deployable cash, for a real one)."""
    settings = get_settings(session)
    bucket = _bucket(session, bucket_id)
    model = bucket.model
    if model is None:
        raise InvalidCash(f"choose a model for {bucket.name} first")
    if amount is None:
        if bucket.paper:
            raise InvalidCash("type the amount to invest on paper")
        amount = cash_total(session, "deployable")
    if amount < 0:
        raise InvalidCash("the amount can't be below 0")
    if not bucket.paper:
        _check_emergency_fund(model, settings.emergency_fund)

    status = emergency(session)
    values = [(m, fund_value(session, m.instrument, bucket.id)) for m in model.funds]
    plan = make_plan(
        amount,
        ZERO if bucket.paper else status.shortfall,
        [Target(m.instrument_id, m.weight_pct, value.value) for m, value in values],
        minimum=settings.min_per_fund,
        stagger_from=None if bucket.paper else settings.stagger_threshold,
        stagger_months=settings.stagger_months,
        today=today(),
    )
    planned = {m.instrument_id for m in model.funds} | {settings.emergency_fund_id}
    others = session.scalars(
        select(Instrument)
        .where(Instrument.id.in_(set(held_ids(session, bucket.id)) - planned))
        .order_by(Instrument.name)
    )
    ignored = [value for i in others if (value := fund_value(session, i, bucket.id)).units > 0]
    return CashPlan(
        amount=amount,
        bucket=bucket,
        model=model,
        emergency=status,
        emergency_topup=plan.emergency,
        funds=[
            FundPlan(now=value, weight=m.weight_pct, invest=plan.split.get(m.instrument_id, ZERO))
            for m, value in values
        ],
        left=plan.left,
        months=plan.months,
        ignored=ignored,
        settings=settings,
    )


def buy_on_paper(session: Session, bucket_id: int, amount: Decimal) -> list[Lot]:
    """Buy a paper bucket's plan for ``amount``: one purchase per fund that gets money, at
    the fund's latest stored NAV and on that NAV's date."""
    bucket = _bucket(session, bucket_id)
    if not bucket.paper:
        raise InvalidCash(f"{bucket.name} holds real money; buy in FM and sync")
    plan = cash_plan(session, bucket_id, amount)
    bought = []
    for fund in plan.funds:
        if fund.invest <= 0:
            continue
        if fund.now.nav is None or fund.now.nav_date is None:
            raise InvalidCash(f"Friday has no NAV for {fund.now.instrument.name}; sync NAVs first")
        data = BuyInput(
            buy_date=fund.now.nav_date, amount=fund.invest, nav=fund.now.nav, bucket_id=bucket.id
        )
        try:
            bought.append(create_lump_sum(session, fund.now.instrument.id, data))
        except InvalidHolding as error:
            raise InvalidCash(str(error)) from None
    if not bought:
        raise InvalidCash("the plan buys nothing; try a larger amount")
    return bought
