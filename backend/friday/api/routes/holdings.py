"""Fund holdings: lump sums, SIPs and units sold from lots."""

from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Literal

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from friday.api.deps import SessionDep
from friday.api.routes.buckets import _sentence
from friday.api.schemas import CoverageOut, FundRef
from friday.core.holdings.models import Lot, LotSale, Sip
from friday.core.holdings.service import (
    CENT,
    BuyInput,
    Holding,
    HoldingConflict,
    InvalidHolding,
    SaleInput,
    SipInput,
    create_lump_sum,
    create_sip,
    delete_lot,
    delete_sale,
    delete_sip,
    holding,
    list_holdings,
    remaining_cost,
    sell,
    sip_active,
    sold_cost,
    update_lot,
    update_sip,
)
from friday.core.instruments.models import Instrument
from friday.core.navs.service import coverage
from friday.core.schema_types import Amount, Nav, Units

router = APIRouter(tags=["holdings"])


def _money(value: Decimal) -> Decimal:
    return value.quantize(CENT, ROUND_HALF_UP)


class SaleOut(BaseModel):
    id: int
    sale_date: date
    units: Units
    nav: Nav
    amount: Amount
    """Units × NAV, rounded to the paisa."""
    realised: Amount
    """Amount minus what the units sold cost."""


class LotOut(BaseModel):
    id: int
    kind: Literal["lump_sum", "sip"]
    sip_id: int | None
    buy_date: date
    amount: Amount
    nav: Nav
    units: Units
    units_remaining: Units
    cost_remaining: Amount
    """What the units still held cost: amount × units remaining ÷ units."""
    edited: bool
    """A SIP instalment I changed by hand: rebuilding the SIP keeps it."""
    skipped: bool
    note: str | None
    source: Literal["fm"] | None
    """Copied from the FM app: read-only here."""
    sales: list[SaleOut]


class SipOut(BaseModel):
    id: int
    amount: Amount
    day: int
    start_date: date
    end_date: date | None
    note: str | None
    active: bool
    """No end date, or one that hasn't passed yet."""
    instalments: int
    """Instalments bought so far, skipped ones not counted."""


class HoldingSummaryOut(BaseModel):
    fund: FundRef
    units: Units
    cost: Amount
    lots: int
    active_sips: int
    nav_last: date | None


class HoldingOut(BaseModel):
    fund: FundRef
    units: Units
    cost: Amount
    lots: list[LotOut]
    sips: list[SipOut]
    coverage: CoverageOut


class LotIn(BaseModel):
    buy_date: date
    amount: Amount
    nav: Nav | None = None
    """Blank: the fund's NAV on that date from the stored history."""
    units: Units | None = None
    """Blank: amount ÷ NAV rounded to 3 places, as AMCs allot."""
    note: str | None = Field(default=None, max_length=200)


class LumpSumIn(LotIn):
    instrument_id: int


class LotEditIn(LotIn):
    skipped: bool = False
    """Mark a SIP instalment as one that didn't happen."""


class SipEditIn(BaseModel):
    amount: Amount
    day: int = Field(ge=1, le=28)
    start_date: date
    end_date: date | None = None
    note: str | None = Field(default=None, max_length=200)


class SipIn(SipEditIn):
    instrument_id: int


class SaleLotIn(BaseModel):
    lot_id: int
    units: Units


class SaleIn(BaseModel):
    sale_date: date
    nav: Nav | None = None
    """Blank: the fund's NAV on the sale date from the stored history."""
    lots: list[SaleLotIn] = Field(min_length=1)


def _ref(instrument: Instrument) -> FundRef:
    return FundRef.model_validate(instrument, from_attributes=True)


def _sale(sale: LotSale) -> SaleOut:
    amount = _money(sale.units * sale.nav)
    return SaleOut(
        id=sale.id,
        sale_date=sale.sale_date,
        units=sale.units,
        nav=sale.nav,
        amount=amount,
        realised=_money(amount - sold_cost(sale)),
    )


def _lot(lot: Lot) -> LotOut:
    return LotOut(
        id=lot.id,
        kind="lump_sum" if lot.sip_id is None else "sip",
        sip_id=lot.sip_id,
        buy_date=lot.buy_date,
        amount=lot.amount,
        nav=lot.nav,
        units=lot.units,
        units_remaining=lot.units_remaining,
        cost_remaining=_money(remaining_cost(lot)),
        edited=lot.edited,
        skipped=lot.skipped,
        note=lot.note,
        source=lot.source,
        sales=[_sale(sale) for sale in lot.sales],
    )


def _sip(sip: Sip) -> SipOut:
    return SipOut(
        id=sip.id,
        amount=sip.amount,
        day=sip.day,
        start_date=sip.start_date,
        end_date=sip.end_date,
        note=sip.note,
        active=sip_active(sip),
        instalments=sum(not lot.skipped for lot in sip.instalments),
    )


def _out(session: Session, value: Holding) -> HoldingOut:
    covered = coverage(session, [value.instrument.id])[value.instrument.id]
    return HoldingOut(
        fund=_ref(value.instrument),
        units=value.units,
        cost=value.cost,
        lots=[_lot(lot) for lot in value.lots],
        sips=[_sip(sip) for sip in value.sips],
        coverage=CoverageOut(first=covered.first, last=covered.last, count=covered.count),
    )


def _holding_out(session: Session, instrument: Instrument) -> HoldingOut:
    session.expire_all()  # relationships changed under the objects we loaded
    return _out(session, holding(session, instrument))


def _get(session: Session, model, item_id: int, what: str):
    item = session.get(model, item_id)
    if item is None:
        raise HTTPException(404, f"No {what} with id {item_id}.")
    return item


def _fund(session: Session, instrument_id: int) -> Instrument:
    instrument = _get(session, Instrument, instrument_id, "instrument")
    if not instrument.amfi_code:
        raise HTTPException(422, f"{instrument.name} is not a mutual fund scheme.")
    return instrument


def _do(action, *args):
    try:
        return action(*args)
    except InvalidHolding as error:
        raise HTTPException(422, _sentence(error)) from None
    except HoldingConflict as error:
        raise HTTPException(409, _sentence(error)) from None


def _buy(payload: LotIn) -> BuyInput:
    return BuyInput(
        buy_date=payload.buy_date,
        amount=payload.amount,
        nav=payload.nav,
        units=payload.units,
        note=payload.note,
    )


def _sip_input(payload: SipEditIn) -> SipInput:
    return SipInput(
        amount=payload.amount,
        day=payload.day,
        start_date=payload.start_date,
        end_date=payload.end_date,
        note=payload.note,
    )


@router.get("/holdings", operation_id="listHoldings")
def list_all(session: SessionDep) -> list[HoldingSummaryOut]:
    """Every fund I have a lot or a SIP in, with units and cost of what I still hold."""
    values = list_holdings(session)
    covered = coverage(session, [value.instrument.id for value in values])
    return [
        HoldingSummaryOut(
            fund=_ref(value.instrument),
            units=value.units,
            cost=value.cost,
            lots=sum(not lot.skipped for lot in value.lots),
            active_sips=sum(sip_active(sip) for sip in value.sips),
            nav_last=covered[value.instrument.id].last,
        )
        for value in values
    ]


@router.get("/holdings/{instrument_id}", operation_id="getHolding")
def get(session: SessionDep, instrument_id: int) -> HoldingOut:
    """One fund's lots (oldest first), with what was sold from each, and its SIPs."""
    return _out(session, holding(session, _fund(session, instrument_id)))


@router.post("/lots", status_code=201, operation_id="addLumpSum")
def add_lump_sum(session: SessionDep, payload: LumpSumIn) -> HoldingOut:
    """Record a lump sum. The fund becomes tracked for NAVs."""
    instrument = _fund(session, payload.instrument_id)
    _do(create_lump_sum, session, instrument.id, _buy(payload))
    return _holding_out(session, instrument)


@router.put("/lots/{lot_id}", operation_id="updateLot")
def update(session: SessionDep, lot_id: int, payload: LotEditIn) -> HoldingOut:
    """Change a lot's figures, or skip a SIP instalment. Edited and skipped instalments are
    kept when the SIP is rebuilt."""
    lot = _get(session, Lot, lot_id, "lot")
    _do(lambda: update_lot(session, lot, _buy(payload), skipped=payload.skipped))
    return _holding_out(session, lot.instrument)


@router.delete("/lots/{lot_id}", status_code=204, operation_id="deleteLot")
def delete(session: SessionDep, lot_id: int) -> Response:
    """Delete a lump sum that nothing was sold from."""
    _do(delete_lot, session, _get(session, Lot, lot_id, "lot"))
    return Response(status_code=204)


@router.post("/sips", status_code=201, operation_id="addSip")
def add_sip(session: SessionDep, payload: SipIn) -> HoldingOut:
    """Start a SIP. Instalments are added for every month the stored NAVs cover, and after
    each NAV sync."""
    instrument = _fund(session, payload.instrument_id)
    _do(create_sip, session, instrument.id, _sip_input(payload))
    return _holding_out(session, instrument)


@router.put("/sips/{sip_id}", operation_id="updateSip")
def change_sip(session: SessionDep, sip_id: int, payload: SipEditIn) -> HoldingOut:
    """Change a SIP and rebuild its instalments, keeping edited, skipped and sold ones."""
    sip = _get(session, Sip, sip_id, "SIP")
    _do(update_sip, session, sip, _sip_input(payload))
    return _holding_out(session, sip.instrument)


@router.delete("/sips/{sip_id}", status_code=204, operation_id="deleteSip")
def remove_sip(session: SessionDep, sip_id: int) -> Response:
    """Delete a SIP and its instalments, if nothing was sold from them."""
    _do(delete_sip, session, _get(session, Sip, sip_id, "SIP"))
    return Response(status_code=204)


@router.post("/sales", status_code=201, operation_id="sellUnits")
def add_sale(session: SessionDep, payload: SaleIn) -> HoldingOut:
    """Take units out of the lots picked, all of one fund, on one date."""
    data = SaleInput(
        sale_date=payload.sale_date,
        nav=payload.nav,
        takes=[(item.lot_id, item.units) for item in payload.lots],
    )
    sales = _do(sell, session, data)
    return _holding_out(session, sales[0].lot.instrument)


@router.delete("/sales/{sale_id}", status_code=204, operation_id="deleteSale")
def remove_sale(session: SessionDep, sale_id: int) -> Response:
    """Undo a sale from one lot: its units go back into the lot."""
    _do(delete_sale, session, _get(session, LotSale, sale_id, "sale"))
    return Response(status_code=204)
