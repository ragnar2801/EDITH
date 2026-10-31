"""A small FM database, shaped like FM's own tables (plus a column FM might add one day)."""

import sqlite3
from pathlib import Path

import pytest
from navs.conftest import fetcher, funds  # noqa: F401 (shared fixtures)

SCHEMA = """
CREATE TABLE currencies (id TEXT PRIMARY KEY, name TEXT, code TEXT, symbol TEXT,
    exchange_rate REAL);
CREATE TABLE securities (id TEXT PRIMARY KEY, name TEXT, ticker TEXT, current_price REAL,
    currency_id TEXT, security_type TEXT, market TEXT, is_archived INTEGER, future_col TEXT);
CREATE TABLE accounts (id TEXT PRIMARY KEY, name TEXT, account_type TEXT);
CREATE TABLE transactions (id TEXT PRIMARY KEY, type TEXT, timestamp TEXT, amount REAL,
    currency_id TEXT, security_id TEXT, security_units REAL, security_price_at_transaction REAL,
    security_account_id TEXT, unit_price_at_transaction REAL);
CREATE TABLE lots (id TEXT PRIMARY KEY, security_id TEXT, security_account_id TEXT,
    acquisition_transaction_id TEXT, acquisition_date TEXT, total_units REAL,
    remaining_units REAL, unit_price REAL, total_cost REAL, currency_id TEXT);
CREATE TABLE sell_allocations (id TEXT PRIMARY KEY, sell_transaction_id TEXT, lot_id TEXT,
    allocated_units REAL, allocated_cost REAL);
PRAGMA user_version = 32;
"""


class FmDb:
    """Builds the file; ``path`` is ready to import after any change."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.db = sqlite3.connect(path)
        self.db.executescript(SCHEMA)
        self.db.executemany(
            "INSERT INTO currencies VALUES (?, ?, ?, ?, 1)",
            [("inr", "Rupee", "INR", "₹"), ("usd", "Dollar", "USD", "$")],
        )
        self.db.executemany(
            "INSERT INTO accounts VALUES (?, ?, 'security')",
            [("grow", "grow mf"), ("amma", "Amma IndMoney")],
        )
        self.db.executemany(
            "INSERT INTO securities VALUES (?, ?, ?, 0, 'inr', ?, 'NASDAQ', 0, 'x')",
            [
                ("parag", "Parag flexi cap", "122639", "MF"),
                ("nifty", "UTI nifty", "120716", "MF"),
                ("ghost", "Closed fund", "999999", "MF"),
                ("infy", "Infosys", "INFY", "STOCK"),
            ],
        )
        self.commit()

    def lot(self, lot_id, security, date, units, price, *, account="grow", currency="inr"):
        cost = units * price
        self.db.execute(
            "INSERT INTO transactions VALUES (?, 'BUYSECURITY', ?, ?, ?, ?, ?, NULL, ?, ?)",
            (
                f"t-{lot_id}",
                f"{date}T10:00:00.000",
                cost,
                currency,
                security,
                units,
                account,
                price,
            ),
        )
        self.db.execute(
            "INSERT INTO lots VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (lot_id, security, account, f"t-{lot_id}", f"{date}T00:00:00.000", units, units,
             price, cost, currency),
        )  # fmt: skip
        self.commit()

    def sell(self, sale_id, lot_id, date, units, price):
        security = self.db.execute(
            "SELECT security_id FROM lots WHERE id = ?", (lot_id,)
        ).fetchone()
        self.db.execute(
            "INSERT INTO transactions VALUES (?, 'SELLSECURITY', ?, ?, 'inr', ?, ?, ?, 'grow', ?)",
            (f"t-{sale_id}", f"{date}T11:30:33.264857", units * price, security[0], units, price,
             price),
        )  # fmt: skip
        self.db.execute(
            "INSERT INTO sell_allocations VALUES (?, ?, ?, ?, 0)",
            (sale_id, f"t-{sale_id}", lot_id, units),
        )
        self.db.execute(
            "UPDATE lots SET remaining_units = remaining_units - ? WHERE id = ?", (units, lot_id)
        )
        self.commit()

    def run(self, sql: str, *args) -> None:
        self.db.execute(sql, args)
        self.commit()

    def commit(self) -> None:
        self.db.commit()


@pytest.fixture
def fm(tmp_path: Path):
    db = FmDb(tmp_path / "finance_manager.db")
    yield db
    db.db.close()
