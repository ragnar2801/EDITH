"""Importing an FM database copy into the holdings, and the import log.

FM is where purchases and sales are recorded; Friday keeps a read-only copy. Each import
replaces every FM purchase and sale in one transaction, so a purchase deleted or changed
in FM is gone or changed here too. Purchases and SIPs entered in Friday are left alone.
"""

import json
import os
import shutil
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, sessionmaker

from friday.core.db import session_scope
from friday.core.fm.models import FmImport
from friday.core.fm.snapshot import FmSnapshot, FmSnapshotError, read_snapshot
from friday.core.holdings.models import Lot, LotSale, Sip
from friday.core.instruments.models import Instrument

SOURCE = "fm"
FM_INCOMING = "finance_manager.incoming.db"
"""The file FM's desktop app swaps in for its database when it next starts."""


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


def apply_snapshot(session: Session, snapshot: FmSnapshot) -> ImportResult:
    """Replace the FM purchases and sales with the copy's. The caller commits."""
    result = ImportResult(warnings=list(snapshot.warnings))
    codes = {lot.amfi_code for lot in snapshot.lots}
    funds = {
        instrument.amfi_code: instrument
        for instrument in session.scalars(select(Instrument).where(Instrument.amfi_code.in_(codes)))
    }
    for code in sorted(codes - funds.keys()):
        names = sorted({lot.fund_name for lot in snapshot.lots if lot.amfi_code == code})
        result.warnings.append(
            f"AMFI {code} ({', '.join(names)}) isn't in the fund list; its purchases were left out."
        )

    before = set(session.scalars(select(Lot.source_id).where(Lot.source == SOURCE)))
    old = select(Lot.id).where(Lot.source == SOURCE)
    session.execute(delete(LotSale).where(LotSale.lot_id.in_(old)))
    session.execute(delete(Lot).where(Lot.source == SOURCE))

    now = _now()
    sales_by_lot: dict[str, list] = {}
    for sale in snapshot.sales:
        sales_by_lot.setdefault(sale.lot_id, []).append(sale)
    kept = [lot for lot in snapshot.lots if lot.amfi_code in funds]
    for item in kept:
        sales = sales_by_lot.get(item.id, [])
        lot = Lot(
            instrument_id=funds[item.amfi_code].id,
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


def _copied_at(path: Path) -> datetime:
    return datetime.fromtimestamp(path.stat().st_mtime, UTC)


def import_file(
    factory: sessionmaker[Session], path: Path, *, skip_accounts: frozenset[str] = frozenset()
) -> FmImport:
    """Import a copy and log it, failed or not. Raises ``FmSnapshotError`` after logging a
    copy that can't be read."""
    started = _now()
    try:
        snapshot = read_snapshot(path, skip_accounts=skip_accounts)
    except FmSnapshotError as error:
        with session_scope(factory) as session:
            row = FmImport(
                status="failed",
                imported_at=started,
                copied_at=_copied_at(path) if path.is_file() else None,
                message=str(error),
            )
            session.add(row)
        raise
    with session_scope(factory) as session:
        result = apply_snapshot(session, snapshot)
        row = FmImport(
            status="ok",
            imported_at=started,
            copied_at=_copied_at(path),
            fm_schema=snapshot.schema,
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


def store_copy(source: Path, destination: Path) -> None:
    """Copy a file into place so nothing ever sees half of it."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    part = destination.with_name(destination.name + ".part")
    shutil.copyfile(source, part)
    os.replace(part, destination)


def handle_push(
    factory: sessionmaker[Session],
    path: Path,
    *,
    forward_dir: Path | None = None,
    skip_accounts: frozenset[str] = frozenset(),
) -> tuple[int, str]:
    """What the receiver does with a copy: import it, hand it to FM desktop, and answer the
    phone with the outcome (FM shows anything but 200 as an error). A copy Friday can't read
    isn't handed on: FM desktop would swap it in for its database."""
    try:
        row = import_file(factory, path, skip_accounts=skip_accounts)
    except FmSnapshotError as error:
        return 422, f"Friday couldn't read the copy: {error}"
    if forward_dir is not None:
        store_copy(path, forward_dir / FM_INCOMING)
    text = f"Friday imported {row.lots} purchases and {row.sales} sales of {row.funds} funds"
    warnings = json.loads(row.warnings)
    if warnings:
        text += f" ({len(warnings)} to check in Friday)"
    return 200, text + "."
