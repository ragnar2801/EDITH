"""Lump sums, SIPs and selling units from lots.

Every buy is a lot with a stored ``units_remaining``. A sale takes units out of the lots I
pick and is kept per lot, so the balance can be put back if I delete it. SIP instalments
are lots too: Friday adds one per month on the first NAV date on or after the SIP day,
as far as the stored NAVs go, and leaves alone the ones I edited or skipped.

Only ``navs.models`` is imported from the NAV package: the NAV service imports this
module to track held funds and to add instalments after a sync.
"""

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from friday.core.holdings.models import Lot, LotSale, Sip
from friday.core.instruments.models import Instrument
from friday.core.navs.models import FundNav
from friday.core.schema_types import IST

ZERO = Decimal(0)
CENT = Decimal("0.01")
ALLOTTED = Decimal("0.001")
"""AMCs allot units to 3 decimal places."""

NAV_WINDOW = timedelta(days=10)
"""How far after a SIP's due date its NAV may be: long enough for any run of holidays."""

HOLDING = "holding"
"""Tracking reason for a fund I hold or have a SIP in."""


class InvalidHolding(ValueError):
    pass


class HoldingConflict(ValueError):
    """The change would contradict units already sold."""


@dataclass(frozen=True)
class BuyInput:
    buy_date: date
    amount: Decimal
    nav: Decimal | None = None
    units: Decimal | None = None
    note: str | None = None


@dataclass(frozen=True)
class SipInput:
    amount: Decimal
    day: int
    start_date: date
    end_date: date | None = None
    note: str | None = None


@dataclass(frozen=True)
class SaleInput:
    sale_date: date
    takes: list[tuple[int, Decimal]]
    """(lot id, units) for every lot units are taken from."""
    nav: Decimal | None = None


def _now() -> datetime:
    return datetime.now(UTC)


def today() -> date:
    """Today in India, where NAV dates live."""
    return datetime.now(IST).date()


def _note(text: str | None) -> str | None:
    return (text or "").strip() or None


def _fund(session: Session, instrument_id: int) -> Instrument:
    instrument = session.get(Instrument, instrument_id)
    if instrument is None:
        raise InvalidHolding(f"no instrument with id {instrument_id}")
    if not instrument.amfi_code:
        raise InvalidHolding(f"{instrument.name} is not a mutual fund scheme")
    return instrument


def _not_future(day: date, what: str) -> None:
    if day > today():
        raise InvalidHolding(f"the {what} date can't be in the future")


def nav_on(session: Session, instrument_id: int, day: date) -> Decimal | None:
    return session.scalar(
        select(FundNav.nav).where(FundNav.instrument_id == instrument_id, FundNav.nav_date == day)
    )


def allotted_units(amount: Decimal, nav: Decimal) -> Decimal:
    return (amount / nav).quantize(ALLOTTED, ROUND_HALF_UP)


def _priced(session: Session, instrument: Instrument, data: BuyInput) -> tuple[Decimal, Decimal]:
    """The buy's NAV and units, filling in whichever is blank."""
    _not_future(data.buy_date, "buy")
    if data.amount <= 0:
        raise InvalidHolding("the amount must be more than 0")
    nav = data.nav
    if nav is None:
        nav = nav_on(session, instrument.id, data.buy_date)
        if nav is None:
            raise InvalidHolding(
                f"Friday has no NAV for {instrument.name} on {data.buy_date:%d %b %Y}; type it in"
            )
    if nav <= 0:
        raise InvalidHolding("the NAV must be more than 0")
    units = data.units if data.units is not None else allotted_units(data.amount, nav)
    if units <= 0:
        raise InvalidHolding("the units must be more than 0")
    return nav, units


def _sold(lot: Lot) -> Decimal:
    return sum((sale.units for sale in lot.sales), ZERO)


def _not_copied(lot: Lot) -> None:
    """Purchases copied from another app are changed there, not here."""
    if lot.source == "fm":
        raise HoldingConflict("this purchase comes from FM; change it there")


# Lump sums and editing any lot ------------------------------------------------------------


def create_lump_sum(session: Session, instrument_id: int, data: BuyInput) -> Lot:
    instrument = _fund(session, instrument_id)
    nav, units = _priced(session, instrument, data)
    now = _now()
    lot = Lot(
        instrument_id=instrument.id,
        buy_date=data.buy_date,
        amount=data.amount,
        nav=nav,
        units=units,
        units_remaining=units,
        note=_note(data.note),
        created_at=now,
        updated_at=now,
    )
    session.add(lot)
    session.flush()
    return lot


def update_lot(session: Session, lot: Lot, data: BuyInput, *, skipped: bool = False) -> Lot:
    """Change a lot's figures. For a SIP instalment this marks it edited (or skipped), so
    rebuilding the SIP leaves it as it is."""
    _not_copied(lot)
    sold = _sold(lot)
    if skipped:
        if lot.sip_id is None:
            raise InvalidHolding("only a SIP instalment can be skipped; delete a lump sum instead")
        if sold:
            raise HoldingConflict("units of this instalment were sold; delete those sales first")
        lot.skipped, lot.edited = True, True
        lot.units = lot.units_remaining = ZERO
        lot.note = _note(data.note)
        lot.updated_at = _now()
        session.flush()
        return lot

    nav, units = _priced(session, lot.instrument, data)
    if units < sold:
        raise HoldingConflict(
            f"{sold.normalize():f} units of this lot were already sold; it can't have fewer"
        )
    first_sale = min((sale.sale_date for sale in lot.sales), default=None)
    if first_sale is not None and data.buy_date > first_sale:
        raise HoldingConflict("the buy date can't be after a sale from this lot")
    lot.buy_date, lot.amount, lot.nav, lot.units = data.buy_date, data.amount, nav, units
    lot.units_remaining = units - sold
    lot.note = _note(data.note)
    lot.skipped = False
    lot.edited = lot.sip_id is not None
    lot.updated_at = _now()
    session.flush()
    return lot


def delete_lot(session: Session, lot: Lot) -> None:
    _not_copied(lot)
    if lot.sip_id is not None:
        raise InvalidHolding("a SIP instalment can't be deleted; skip it instead")
    if lot.sales:
        raise HoldingConflict("units of this lot were sold; delete those sales first")
    session.delete(lot)
    session.flush()


# SIPs -------------------------------------------------------------------------------------


def _validate_sip(data: SipInput) -> None:
    if data.amount <= 0:
        raise InvalidHolding("the SIP amount must be more than 0")
    if not 1 <= data.day <= 28:
        raise InvalidHolding("the SIP day must be from 1 to 28")
    _not_future(data.start_date, "start")
    if data.end_date is not None and data.end_date < data.start_date:
        raise InvalidHolding("the end date can't be before the start date")


def sip_active(sip: Sip) -> bool:
    return sip.end_date is None or sip.end_date >= today()


def next_due(sip: Sip, after: date) -> date | None:
    """The SIP's first due date on or after ``after``; ``None`` once it has ended."""
    if not sip_active(sip):
        return None
    return next(due_dates(max(sip.start_date, after), sip.day, sip.end_date, date.max), None)


def due_dates(start: date, day: int, end: date | None, until: date) -> Iterator[date]:
    """The SIP's due dates from ``start`` to ``end`` (or ``until``), both inclusive."""
    year, month = start.year, start.month
    last = min(end, until) if end else until
    while (due := date(year, month, day)) <= last:
        if due >= start:
            yield due
        year, month = (year + 1, 1) if month == 12 else (year, month + 1)


def instalment_dates(
    nav_dates: list[date], start: date, day: int, end: date | None
) -> list[tuple[date, date]]:
    """(due date, NAV date) for every instalment the NAVs cover: the first NAV date on or
    after the due date, if it is within ``NAV_WINDOW`` days. A month without one (a gap in
    the data, or before the fund's first NAV) has no instalment; months after the last NAV
    wait for the next sync. ``nav_dates`` must be sorted."""
    if not nav_dates:
        return []
    found = []
    i = 0
    for due in due_dates(start, day, end, nav_dates[-1]):
        while nav_dates[i] < due:
            i += 1
        if nav_dates[i] - due <= NAV_WINDOW:
            found.append((due, nav_dates[i]))
    return found


def _add_instalments(session: Session, sip: Sip) -> int:
    navs = dict(
        session.execute(
            select(FundNav.nav_date, FundNav.nav)
            .where(FundNav.instrument_id == sip.instrument_id, FundNav.nav_date >= sip.start_date)
            .order_by(FundNav.nav_date)
        ).all()
    )
    have = {lot.due_month for lot in sip.instalments}
    now = _now()
    added = 0
    for due, nav_date in instalment_dates(list(navs), sip.start_date, sip.day, sip.end_date):
        month = due.replace(day=1)
        if month in have:
            continue
        nav = navs[nav_date]
        units = allotted_units(sip.amount, nav)
        sip.instalments.append(
            Lot(
                instrument_id=sip.instrument_id,
                due_month=month,
                buy_date=nav_date,
                amount=sip.amount,
                nav=nav,
                units=units,
                units_remaining=units,
                created_at=now,
                updated_at=now,
            )
        )
        added += 1
    session.flush()
    return added


def add_due_instalments(session: Session) -> int:
    """Add every SIP instalment the stored NAVs now cover. Run after each NAV sync."""
    return sum(_add_instalments(session, sip) for sip in session.scalars(select(Sip)))


def create_sip(session: Session, instrument_id: int, data: SipInput) -> Sip:
    instrument = _fund(session, instrument_id)
    _validate_sip(data)
    now = _now()
    sip = Sip(
        instrument_id=instrument.id,
        amount=data.amount,
        day=data.day,
        start_date=data.start_date,
        end_date=data.end_date,
        note=_note(data.note),
        created_at=now,
        updated_at=now,
    )
    session.add(sip)
    session.flush()
    _add_instalments(session, sip)
    return sip


def update_sip(session: Session, sip: Sip, data: SipInput) -> Sip:
    """Change the SIP and rebuild its instalments, keeping the ones I edited, skipped or
    sold from. Sold instalments outside the new dates are refused."""
    _validate_sip(data)
    dues = {
        due.replace(day=1) for due in due_dates(data.start_date, data.day, data.end_date, today())
    }
    kept = []
    for lot in sip.instalments:
        inside = lot.due_month in dues
        if lot.sales and not inside:
            raise HoldingConflict(
                f"units of the {lot.due_month:%b %Y} instalment were sold; "
                "the SIP's dates must still include it"
            )
        if lot.sales or (inside and lot.edited):
            kept.append(lot)
    sip.instalments = kept
    sip.amount, sip.day = data.amount, data.day
    sip.start_date, sip.end_date = data.start_date, data.end_date
    sip.note = _note(data.note)
    sip.updated_at = _now()
    session.flush()
    _add_instalments(session, sip)
    return sip


def delete_sip(session: Session, sip: Sip) -> None:
    if any(lot.sales for lot in sip.instalments):
        raise HoldingConflict("units of this SIP were sold; delete those sales first")
    session.delete(sip)
    session.flush()


# Selling ----------------------------------------------------------------------------------


def sell(session: Session, data: SaleInput) -> list[LotSale]:
    """Take units out of the lots picked, all from one fund, on one date."""
    if not data.takes:
        raise InvalidHolding("pick at least one lot to sell from")
    ids = [lot_id for lot_id, _ in data.takes]
    if len(set(ids)) != len(ids):
        raise InvalidHolding("a lot is listed twice")
    _not_future(data.sale_date, "sale")
    lots = []
    for lot_id, units in data.takes:
        lot = session.get(Lot, lot_id)
        if lot is None:
            raise InvalidHolding(f"no lot with id {lot_id}")
        _not_copied(lot)
        if units <= 0:
            raise InvalidHolding("units sold must be more than 0")
        if units > lot.units_remaining:
            raise HoldingConflict(
                f"the {lot.buy_date:%d %b %Y} lot has only "
                f"{lot.units_remaining.normalize():f} units left"
            )
        if data.sale_date < lot.buy_date:
            raise InvalidHolding(f"the sale date is before the {lot.buy_date:%d %b %Y} buy")
        lots.append((lot, units))
    if len({lot.instrument_id for lot, _ in lots}) > 1:
        raise InvalidHolding("all lots in one sale must be of the same fund")

    instrument = lots[0][0].instrument
    nav = data.nav if data.nav is not None else nav_on(session, instrument.id, data.sale_date)
    if nav is None:
        raise InvalidHolding(
            f"Friday has no NAV for {instrument.name} on {data.sale_date:%d %b %Y}; type it in"
        )
    if nav <= 0:
        raise InvalidHolding("the NAV must be more than 0")
    now = _now()
    sales = []
    for lot, units in lots:
        lot.units_remaining -= units
        lot.updated_at = now
        sale = LotSale(lot=lot, sale_date=data.sale_date, units=units, nav=nav, created_at=now)
        session.add(sale)
        sales.append(sale)
    session.flush()
    return sales


def delete_sale(session: Session, sale: LotSale) -> None:
    """Undo one take: its units go back into the lot."""
    _not_copied(sale.lot)
    sale.lot.units_remaining += sale.units
    sale.lot.updated_at = _now()
    session.delete(sale)
    session.flush()


# Reading ----------------------------------------------------------------------------------


@dataclass(frozen=True)
class Holding:
    instrument: Instrument
    units: Decimal
    cost: Decimal
    """What the units still held cost: each lot's amount × units remaining ÷ units."""
    lots: list[Lot]
    sips: list[Sip]


def remaining_cost(lot: Lot) -> Decimal:
    return lot.amount * lot.units_remaining / lot.units if lot.units else ZERO


def sold_cost(sale: LotSale) -> Decimal:
    """What the units of one sale cost when bought (exact)."""
    lot = sale.lot
    return lot.amount * sale.units / lot.units if lot.units else ZERO


def _holding(instrument: Instrument, lots: list[Lot], sips: list[Sip]) -> Holding:
    bought = [lot for lot in lots if not lot.skipped]
    return Holding(
        instrument=instrument,
        units=sum((lot.units_remaining for lot in bought), ZERO),
        cost=sum((remaining_cost(lot) for lot in bought), ZERO).quantize(CENT, ROUND_HALF_UP),
        lots=lots,
        sips=sips,
    )


def holding(session: Session, instrument: Instrument) -> Holding:
    lots = session.scalars(
        select(Lot).where(Lot.instrument_id == instrument.id).order_by(Lot.buy_date, Lot.id)
    ).all()
    sips = session.scalars(
        select(Sip).where(Sip.instrument_id == instrument.id).order_by(Sip.start_date, Sip.id)
    ).all()
    return _holding(instrument, list(lots), list(sips))


def held_ids(session: Session) -> list[int]:
    return list(session.scalars(select(Lot.instrument_id).union(select(Sip.instrument_id))))


def list_holdings(session: Session) -> list[Holding]:
    """Every fund I have a lot or a SIP in, by name."""
    ids = held_ids(session)
    instruments = session.scalars(
        select(Instrument).where(Instrument.id.in_(ids)).order_by(Instrument.name)
    )
    return [holding(session, instrument) for instrument in instruments]


def holding_reasons(session: Session) -> dict[int, list[str]]:
    return {instrument_id: [HOLDING] for instrument_id in held_ids(session)}
