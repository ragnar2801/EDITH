"""Reading a copy of FM's database. Read-only, no Friday tables touched.

FM's tables are read as they are: columns are looked up by name, so columns FM adds later
are ignored, and only a renamed or removed column breaks the import. FM stores money as
floats; each value goes through its shortest decimal form (``repr``) and is rounded to the
places Friday keeps, so ``63007.451199999996`` becomes ``63007.45``.
"""

import sqlite3
from dataclasses import dataclass, field
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

# Remaining units FM stored and units bought less units sold may differ by float noise.
UNITS_SLACK = Decimal("0.001")
TABLES = ("securities", "accounts", "currencies", "transactions", "lots", "sell_allocations")


class FmSnapshotError(ValueError):
    """The file isn't an FM database copy Friday can read."""


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


@dataclass(frozen=True)
class FmSale:
    id: str
    lot_id: str
    sale_date: date
    units: Decimal
    nav: Decimal


@dataclass
class FmSnapshot:
    schema: int
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


def _rows(db: sqlite3.Connection, table: str) -> list[dict]:
    return [dict(row) for row in db.execute(f"SELECT * FROM {table}")]  # noqa: S608 (fixed names)


def _open(path: Path) -> sqlite3.Connection:
    if not path.is_file():
        raise FmSnapshotError(f"no file at {path}")
    with path.open("rb") as file:
        if file.read(16) != b"SQLite format 3\x00":
            raise FmSnapshotError(f"{path.name} isn't a database file")
    db = sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    return db


def read_snapshot(path: Path, *, skip_accounts: frozenset[str] = frozenset()) -> FmSnapshot:
    """Every mutual fund purchase in the copy and what was sold from it. ``skip_accounts``
    are FM account names (any case) whose purchases are left out."""
    db = _open(path)
    try:
        present = {
            row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        missing = [table for table in TABLES if table not in present]
        if missing:
            raise FmSnapshotError(f"not an FM database: no {', '.join(missing)} table")
        snapshot = FmSnapshot(schema=db.execute("PRAGMA user_version").fetchone()[0])
        try:
            _read(db, snapshot, {name.strip().casefold() for name in skip_accounts})
        except (sqlite3.Error, KeyError) as error:
            raise FmSnapshotError(f"FM's tables have changed: {error}") from None
        return snapshot
    finally:
        db.close()


def _read(db: sqlite3.Connection, snapshot: FmSnapshot, skip: set[str]) -> None:
    funds = {
        row["id"]: row
        for row in _rows(db, "securities")
        if str(row["security_type"]).upper() == "MF"
    }
    accounts = {row["id"]: str(row["name"]).strip() for row in _rows(db, "accounts")}
    currencies = {row["id"]: str(row["code"]).upper() for row in _rows(db, "currencies")}
    transactions = {row["id"]: row for row in _rows(db, "transactions")}

    held: dict[str, FmLot] = {}
    stored_remaining: dict[str, Decimal] = {}
    for row in _rows(db, "lots"):
        fund = funds.get(row["security_id"])
        if fund is None:
            continue
        account = accounts.get(row["security_account_id"], "")
        if account.casefold() in skip:
            continue
        name = str(fund["name"]).strip()
        code = str(fund["ticker"] or "").strip()
        currency = currencies.get(row["currency_id"], "")
        units = decimal(row["total_units"], 8)
        nav = decimal(row["unit_price"], 8)
        amount = decimal(row["total_cost"], 2)
        if amount is None and units is not None and nav is not None:
            amount = decimal(units * nav, 2)
        if nav is None and amount is not None and units:
            nav = decimal(amount / units, 8)
        buy_date = _day(row["acquisition_date"])
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
            snapshot.warnings.append(f"A purchase of {name} {problem}; it was left out.")
            continue
        held[row["id"]] = FmLot(
            id=row["id"],
            amfi_code=code,
            fund_name=name,
            account=account,
            buy_date=buy_date,
            amount=amount,
            nav=nav,
            units=units,
        )
        stored_remaining[row["id"]] = decimal(row["remaining_units"], 8) or Decimal(0)

    sold: dict[str, Decimal] = {}
    for row in _rows(db, "sell_allocations"):
        lot = held.get(row["lot_id"])
        if lot is None:
            continue
        sell = transactions.get(row["sell_transaction_id"])
        units = decimal(row["allocated_units"], 8)
        nav = None
        if sell is not None:
            nav = decimal(sell["unit_price_at_transaction"], 8) or decimal(
                sell["security_price_at_transaction"], 8
            )
            if nav is None and sell["security_units"]:
                nav = decimal(
                    Decimal(repr(sell["amount"])) / Decimal(repr(sell["security_units"])), 8
                )
        sale_date = _day(sell["timestamp"]) if sell is not None else None
        if not (units and units > 0 and nav and nav > 0 and sale_date):
            snapshot.warnings.append(
                f"A sale of {lot.fund_name} has no date, units or NAV; it was left out."
            )
            continue
        snapshot.sales.append(
            FmSale(id=row["id"], lot_id=lot.id, sale_date=sale_date, units=units, nav=nav)
        )
        sold[lot.id] = sold.get(lot.id, Decimal(0)) + units

    for lot in held.values():
        left = lot.units - sold.get(lot.id, Decimal(0))
        if left < 0:
            snapshot.warnings.append(
                f"More units of the {lot.buy_date:%d %b %Y} {lot.fund_name} purchase were sold "
                "than bought; it was left out."
            )
            snapshot.sales = [sale for sale in snapshot.sales if sale.lot_id != lot.id]
            continue
        if abs(left - stored_remaining[lot.id]) > UNITS_SLACK:
            snapshot.warnings.append(
                f"FM shows {stored_remaining[lot.id].normalize():f} units left in the "
                f"{lot.buy_date:%d %b %Y} {lot.fund_name} purchase; its sales leave "
                f"{left.normalize():f}. Friday uses its sales."
            )
        snapshot.lots.append(lot)
