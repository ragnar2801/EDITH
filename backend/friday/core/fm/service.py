"""Importing FM's lots feed into the holdings, and the import log.

FM is where purchases and sales are recorded; Friday keeps a read-only copy in its own
tables. Each import deletes every FM purchase and sale and adds the feed's, in one
transaction, so a purchase deleted or changed in FM is gone or changed here too. Purchases
and SIPs entered in Friday are left alone. A purchase FM put in a bucket goes in the Friday
bucket made for it (see ``buckets.service.fm_bucket``). The feed itself isn't kept.
"""

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, sessionmaker

from friday.core.buckets.service import fm_bucket
from friday.core.db import session_scope
from friday.core.fm.feed import FmFeed, FmFeedError, read_feed
from friday.core.fm.models import FmImport
from friday.core.holdings.models import Lot, LotSale, Sip
from friday.core.instruments.models import Instrument

SOURCE = "fm"


@dataclass
class ImportResult:
    funds: int = 0
    lots: int = 0
    sales: int = 0
    added: int = 0
    removed: int = 0
    warnings: list[str] = field(default_factory=list)


def _now() -> datetime:
    return datetime.now(UTC)


def apply_feed(session: Session, feed: FmFeed) -> ImportResult:
    """Replace the FM purchases and sales with the feed's. The caller commits."""
    result = ImportResult(warnings=list(feed.warnings))
    codes = {lot.amfi_code for lot in feed.lots}
    funds = {
        instrument.amfi_code: instrument
        for instrument in session.scalars(select(Instrument).where(Instrument.amfi_code.in_(codes)))
    }
    for code in sorted(codes - funds.keys()):
        names = sorted({lot.fund_name for lot in feed.lots if lot.amfi_code == code})
        result.warnings.append(
            f"AMFI {code} ({', '.join(names)}) isn't in the fund list; its purchases were left out."
        )

    before = set(session.scalars(select(Lot.source_id).where(Lot.source == SOURCE)))
    old = select(Lot.id).where(Lot.source == SOURCE)
    session.execute(delete(LotSale).where(LotSale.lot_id.in_(old)))
    session.execute(delete(Lot).where(Lot.source == SOURCE))

    now = _now()
    sales_by_lot: dict[str, list] = {}
    for sale in feed.sales:
        sales_by_lot.setdefault(sale.lot_id, []).append(sale)
    kept = [lot for lot in feed.lots if lot.amfi_code in funds]
    names = {item.bucket_id: item.bucket_name for item in kept if item.bucket_id}
    buckets = {fm_id: fm_bucket(session, fm_id, name or "").id for fm_id, name in names.items()}
    for item in kept:
        sales = sales_by_lot.get(item.id, [])
        lot = Lot(
            instrument_id=funds[item.amfi_code].id,
            bucket_id=buckets.get(item.bucket_id or ""),
            buy_date=item.buy_date,
            amount=item.amount,
            nav=item.nav,
            units=item.units,
            units_remaining=item.units - sum((sale.units for sale in sales), Decimal(0)),
            note=item.account or None,
            source=SOURCE,
            source_id=item.id,
            created_at=now,
            updated_at=now,
        )
        lot.sales = [
            LotSale(
                sale_date=sale.sale_date,
                units=sale.units,
                nav=sale.nav,
                source_id=sale.id,
                created_at=now,
            )
            for sale in sales
        ]
        session.add(lot)
        result.sales += len(sales)
    session.flush()

    after = {lot.id for lot in kept}
    result.funds = len({lot.amfi_code for lot in kept})
    result.lots = len(kept)
    result.added = len(after - before)
    result.removed = len(before - after)

    ids = [funds[code].id for code in {lot.amfi_code for lot in kept}]
    mixed = session.scalars(
        select(Instrument.name)
        .where(Instrument.id.in_(ids))
        .where(
            Instrument.id.in_(select(Lot.instrument_id).where(Lot.source.is_(None)))
            | Instrument.id.in_(select(Sip.instrument_id))
        )
        .order_by(Instrument.name)
    ).all()
    for name in mixed:
        result.warnings.append(
            f"{name} also has purchases or SIPs entered in Friday; they count alongside FM's."
        )
    return result


def import_feed(factory: sessionmaker[Session], body: bytes | str) -> FmImport:
    """Import a feed and log it, failed or not. Raises ``FmFeedError`` after logging a feed
    that can't be read."""
    started = _now()
    try:
        feed = read_feed(body)
    except FmFeedError as error:
        with session_scope(factory) as session:
            session.add(FmImport(status="failed", imported_at=started, message=str(error)))
        raise
    with session_scope(factory) as session:
        result = apply_feed(session, feed)
        row = FmImport(
            status="ok",
            imported_at=started,
            sent_at=feed.sent_at,
            fm_schema=feed.fm_schema,
            funds=result.funds,
            lots=result.lots,
            sales=result.sales,
            added=result.added,
            removed=result.removed,
            warnings=json.dumps(result.warnings),
        )
        session.add(row)
    return row


def last_import(session: Session) -> FmImport | None:
    return session.scalar(select(FmImport).order_by(FmImport.id.desc()).limit(1))


def handle_push(factory: sessionmaker[Session], body: bytes) -> tuple[int, str]:
    """What the receiver does with a feed: import it and answer the phone with the outcome
    (FM shows anything but 200 as an error)."""
    try:
        row = import_feed(factory, body)
    except FmFeedError as error:
        return 422, f"Friday couldn't read the lots: {error}"
    text = f"Friday imported {row.lots} purchases and {row.sales} sales of {row.funds} funds"
    warnings = json.loads(row.warnings)
    if warnings:
        text += f" ({len(warnings)} to check in Friday)"
    return 200, text + "."
