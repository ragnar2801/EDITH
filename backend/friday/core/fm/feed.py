"""Reading the lots feed FM sends: every investment lot with its sales, as JSON.

Each lot carries FM's own row (every column of ``lots``) with its ``security``,
``account``, ``currency`` and ``acquisition`` rows nested in, the ``bucket`` its purchase
was put in (``id`` and ``name``; null or missing for none), and ``sales``: each sell
allocation with its sell ``transaction``. Fields are looked up by name, so fields FM adds
later are ignored; only a renamed or removed one breaks the import. Numbers are read as
decimals straight from the JSON and rounded to the places Friday keeps, so FM's float noise
(``63007.451199999996``) becomes ``63007.45``.
"""

import json
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal

FORMAT = "fm-lots"
VERSION = 1
# Remaining units FM stored and units bought less units sold may differ by float noise.
UNITS_SLACK = Decimal("0.001")


class FmFeedError(ValueError):
    """The body isn't a lots feed Friday can read."""


@dataclass(frozen=True)
class FmLot:
    id: str
    amfi_code: str
    fund_name: str
    account: str
    buy_date: date
    amount: Decimal
    nav: Decimal
    units: Decimal
    bucket_id: str | None = None
    bucket_name: str | None = None


@dataclass(frozen=True)
class FmSale:
    id: str
    lot_id: str
    sale_date: date
    units: Decimal
    nav: Decimal


@dataclass
class FmFeed:
    sent_at: datetime | None
    fm_schema: int | None
    lots: list[FmLot] = field(default_factory=list)
    sales: list[FmSale] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def decimal(value: object, places: int) -> Decimal | None:
    if value is None or value == "":
        return None
    text = repr(value) if isinstance(value, float) else str(value)
    return Decimal(text).quantize(Decimal(1).scaleb(-places), ROUND_HALF_UP)


def _day(value: object) -> date | None:
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def _moment(value: object) -> datetime | None:
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def read_feed(body: bytes | str) -> FmFeed:
    """Every mutual fund purchase in the feed and what was sold from it."""
    try:
        data = json.loads(body, parse_float=Decimal)
    except ValueError, UnicodeDecodeError:
        raise FmFeedError("it isn't JSON") from None
    if not isinstance(data, dict) or data.get("format") != FORMAT:
        raise FmFeedError("it isn't an FM lots feed")
    if data.get("version") != VERSION:
        raise FmFeedError(f"FM sent version {data.get('version')}; Friday reads {VERSION}")
    if not isinstance(data.get("lots"), list):
        raise FmFeedError("it has no lots")
    feed = FmFeed(sent_at=_moment(data.get("sent_at")), fm_schema=data.get("fm_schema"))
    try:
        _read(data["lots"], feed)
    except (KeyError, TypeError, AttributeError) as error:
        raise FmFeedError(f"FM's lots have changed: {error}") from None
    return feed


def _read(items: list[dict], feed: FmFeed) -> None:
    sold: dict[str, Decimal] = {}
    stored_remaining: dict[str, Decimal] = {}
    held: dict[str, FmLot] = {}
    for item in items:
        security = item["security"] or {}
        if str(security.get("security_type", "")).upper() != "MF":
            continue
        lot = _lot(item, security, feed)
        if lot is None:
            continue
        held[lot.id] = lot
        stored_remaining[lot.id] = decimal(item["remaining_units"], 8) or Decimal(0)
        for sale in item.get("sales") or []:
            taken = _sale(sale, lot, feed)
            if taken is not None:
                feed.sales.append(taken)
                sold[lot.id] = sold.get(lot.id, Decimal(0)) + taken.units

    for lot in held.values():
        left = lot.units - sold.get(lot.id, Decimal(0))
        if left < 0:
            feed.warnings.append(
                f"More units of the {lot.buy_date:%d %b %Y} {lot.fund_name} purchase were sold "
                "than bought; it was left out."
            )
            feed.sales = [sale for sale in feed.sales if sale.lot_id != lot.id]
            continue
        if abs(left - stored_remaining[lot.id]) > UNITS_SLACK:
            feed.warnings.append(
                f"FM shows {stored_remaining[lot.id].normalize():f} units left in the "
                f"{lot.buy_date:%d %b %Y} {lot.fund_name} purchase; its sales leave "
                f"{left.normalize():f}. Friday uses its sales."
            )
        feed.lots.append(lot)


def _lot(item: dict, security: dict, feed: FmFeed) -> FmLot | None:
    name = str(security["name"]).strip()
    code = str(security.get("ticker") or "").strip()
    currency = str((item.get("currency") or {}).get("code") or "").upper()
    units = decimal(item["total_units"], 8)
    nav = decimal(item["unit_price"], 8)
    amount = decimal(item["total_cost"], 2)
    if amount is None and units is not None and nav is not None:
        amount = decimal(units * nav, 2)
    if nav is None and amount is not None and units:
        nav = decimal(amount / units, 8)
    buy_date = _day(item["acquisition_date"])
    problem = None
    if not code:
        problem = "has no AMFI scheme code"
    elif currency != "INR":
        problem = f"is in {currency or 'an unknown currency'}"
    elif buy_date is None:
        problem = "has no purchase date"
    elif not (units and units > 0 and nav and nav > 0 and amount and amount > 0):
        problem = "has no units, NAV or amount"
    if problem:
        feed.warnings.append(f"A purchase of {name} {problem}; it was left out.")
        return None
    bucket = item.get("bucket") or {}
    bucket_id = str(bucket.get("id") or "").strip() or None
    return FmLot(
        id=str(item["id"]),
        amfi_code=code,
        fund_name=name,
        account=str((item.get("account") or {}).get("name") or "").strip(),
        buy_date=buy_date,
        amount=amount,
        nav=nav,
        units=units,
        bucket_id=bucket_id,
        bucket_name=str(bucket.get("name") or "").strip() if bucket_id else None,
    )


def _sale(sale: dict, lot: FmLot, feed: FmFeed) -> FmSale | None:
    sell = sale.get("transaction") or {}
    units = decimal(sale["allocated_units"], 8)
    nav = decimal(sell.get("unit_price_at_transaction"), 8) or decimal(
        sell.get("security_price_at_transaction"), 8
    )
    if nav is None and sell.get("amount") and sell.get("security_units"):
        nav = decimal(Decimal(str(sell["amount"])) / Decimal(str(sell["security_units"])), 8)
    sale_date = _day(sell.get("timestamp"))
    if not (units and units > 0 and nav and nav > 0 and sale_date):
        feed.warnings.append(
            f"A sale of {lot.fund_name} has no date, units or NAV; it was left out."
        )
        return None
    return FmSale(id=str(sale["id"]), lot_id=lot.id, sale_date=sale_date, units=units, nav=nav)
