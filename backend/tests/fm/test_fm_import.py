"""Importing FM database copies: what comes in, re-imports, and what is left out."""

import json
import sqlite3
from datetime import date
from decimal import Decimal

import pytest
from navs.conftest import PARAG
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from friday.core.db import session_scope
from friday.core.fm.models import FmImport
from friday.core.fm.service import import_file
from friday.core.fm.snapshot import FmSnapshotError, decimal, read_snapshot
from friday.core.holdings.models import Lot
from friday.core.holdings.service import BuyInput, create_lump_sum


def fm_lots(factory: sessionmaker[Session]) -> list[tuple]:
    with session_scope(factory) as session:
        lots = session.scalars(select(Lot).where(Lot.source == "fm").order_by(Lot.buy_date)).all()
        return [
            (
                lot.source_id,
                lot.buy_date,
                lot.amount,
                lot.nav,
                lot.units,
                lot.units_remaining,
                lot.note,
                [(sale.source_id, sale.sale_date, sale.units, sale.nav) for sale in lot.sales],
            )
            for lot in lots
        ]


def test_floats_become_the_decimals_they_were_typed_as() -> None:
    assert decimal(63007.451199999996, 2) == Decimal("63007.45")
    assert decimal(3916.6499999999996, 8) == Decimal("3916.65000000")
    assert decimal(15.7247, 8) == Decimal("15.72470000")
    assert decimal(None, 2) is None


def test_purchases_and_sales_come_in(fm, factory, funds) -> None:
    fm.lot("a", "parag", "2025-04-01", 2642.93, 23.84)
    fm.lot("b", "nifty", "2025-05-08", 100.5, 150.1234)
    fm.sell("s1", "a", "2026-02-14", 642.93, 30.5)
    fm.lot("stock", "infy", "2025-01-01", 10, 1500)  # not a fund: ignored

    row = import_file(factory, fm.path)

    assert (row.status, row.fm_schema, row.funds, row.lots, row.sales) == ("ok", 32, 2, 2, 1)
    assert (row.added, row.removed, json.loads(row.warnings)) == (2, 0, [])
    assert fm_lots(factory) == [
        (
            "a",
            date(2025, 4, 1),
            Decimal("63007.45"),
            Decimal("23.84"),
            Decimal("2642.93"),
            Decimal("2000"),
            "grow mf",
            [("s1", date(2026, 2, 14), Decimal("642.93"), Decimal("30.5"))],
        ),
        (
            "b",
            date(2025, 5, 8),
            Decimal("15087.40"),
            Decimal("150.1234"),
            Decimal("100.5"),
            Decimal("100.5"),
            "grow mf",
            [],
        ),
    ]


def test_importing_again_replaces_what_changed_in_fm(fm, factory, funds) -> None:
    fm.lot("a", "parag", "2025-04-01", 100, 20)
    fm.lot("b", "parag", "2025-05-01", 50, 22)
    import_file(factory, fm.path)
    assert import_file(factory, fm.path).added == 0  # nothing changed: nothing new

    fm.run("UPDATE lots SET total_units = 120, remaining_units = 120 WHERE id = 'a'")
    fm.run("DELETE FROM lots WHERE id = 'b'")
    fm.lot("c", "nifty", "2025-06-01", 10, 200)
    row = import_file(factory, fm.path)

    assert (row.lots, row.added, row.removed) == (2, 1, 1)
    assert [(lot[0], lot[4]) for lot in fm_lots(factory)] == [
        ("a", Decimal("120")),
        ("c", Decimal("10")),
    ]


@pytest.fixture
def own_lot(factory, funds) -> None:
    """A purchase typed into Friday."""
    with session_scope(factory) as session:
        create_lump_sum(
            session,
            funds[PARAG],
            BuyInput(buy_date=date(2026, 1, 6), amount=Decimal(1000), nav=Decimal(80)),
        )


def test_purchases_entered_in_friday_are_left_alone(own_lot, fm, factory, funds) -> None:
    fm.lot("a", "parag", "2025-04-01", 100, 20)
    row = import_file(factory, fm.path)
    with session_scope(factory) as session:
        own = session.scalars(select(Lot).where(Lot.source.is_(None))).all()
        assert len(own) == 1
    assert json.loads(row.warnings) == [
        "Parag Parikh Flexi Cap Fund also has purchases or SIPs entered in Friday; "
        "they count alongside FM's."
    ]


def test_what_cant_be_imported_is_listed(fm, factory, funds) -> None:
    fm.lot("a", "parag", "2025-04-01", 100, 20)
    fm.lot("ghost", "ghost", "2025-04-01", 10, 10)
    fm.lot("usd", "nifty", "2025-04-01", 10, 10, currency="usd")
    fm.lot("odd", "nifty", "2025-04-02", 10, 10)
    fm.run("UPDATE lots SET remaining_units = 4 WHERE id = 'odd'")

    row = import_file(factory, fm.path)

    assert row.lots == 2
    assert json.loads(row.warnings) == [
        "A purchase of UTI nifty is in USD; it was left out.",
        "FM shows 4 units left in the 02 Apr 2025 UTI nifty purchase; its sales leave 10. "
        "Friday uses its sales.",
        "AMFI 999999 (Closed fund) isn't in the fund list; its purchases were left out.",
    ]


def test_accounts_can_be_left_out(fm, factory, funds) -> None:
    fm.lot("mine", "parag", "2025-04-01", 100, 20)
    fm.lot("hers", "parag", "2025-04-02", 100, 20, account="amma")

    row = import_file(factory, fm.path, skip_accounts=frozenset({"amma indmoney"}))

    assert row.lots == 1
    assert [lot[0] for lot in fm_lots(factory)] == ["mine"]


def test_a_file_that_isnt_an_fm_copy_is_logged_and_refused(tmp_path, factory) -> None:
    junk = tmp_path / "junk.db"
    junk.write_text("not a database", encoding="utf-8")
    with pytest.raises(FmSnapshotError, match="isn't a database file"):
        import_file(factory, junk)

    other = tmp_path / "other.db"
    sqlite3.connect(other).execute("CREATE TABLE lots (id TEXT)").connection.close()
    with pytest.raises(FmSnapshotError, match="no securities, accounts"):
        read_snapshot(other)

    with session_scope(factory) as session:
        logged = session.scalars(select(FmImport)).all()
        assert [(row.status, row.message) for row in logged] == [
            ("failed", "junk.db isn't a database file")
        ]


def test_a_removed_column_is_reported(fm, factory, funds) -> None:
    fm.lot("a", "parag", "2025-04-01", 100, 20)
    fm.run("ALTER TABLE lots DROP COLUMN unit_price")
    with pytest.raises(FmSnapshotError, match="FM's tables have changed: 'unit_price'"):
        read_snapshot(fm.path)
