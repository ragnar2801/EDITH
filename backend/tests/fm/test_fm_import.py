"""Importing FM's lots feed: what comes in, re-imports, and what is left out."""

import json
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from navs.conftest import PARAG
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from friday.core.buckets.models import Bucket
from friday.core.buckets.service import BucketInput, create_bucket
from friday.core.db import session_scope
from friday.core.fm.feed import FmFeedError, decimal, read_feed
from friday.core.fm.models import FmImport
from friday.core.fm.service import import_feed
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


def test_float_noise_is_rounded_away() -> None:
    assert decimal(Decimal("63007.451199999996"), 2) == Decimal("63007.45")
    assert decimal(3916.6499999999996, 8) == Decimal("3916.65000000")
    assert decimal(None, 2) is None


def test_purchases_and_sales_come_in(feed, factory, funds) -> None:
    feed.lot("a", "parag", "2025-04-01", 2642.93, 23.84)
    feed.lot("b", "nifty", "2025-05-08", 100.5, 150.1234)
    feed.sell("s1", "a", "2026-02-14", 642.93, 30.5)
    feed.lot("stock", "infy", "2025-01-01", 10, 1500)  # not a fund: ignored

    row = import_feed(factory, feed.body())

    assert (row.status, row.fm_schema, row.funds, row.lots, row.sales) == ("ok", 32, 2, 2, 1)
    assert row.sent_at == datetime(2026, 10, 31, 6, tzinfo=UTC)
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


def test_each_sync_replaces_what_came_from_fm(feed, factory, funds) -> None:
    feed.lot("a", "parag", "2025-04-01", 100, 20)
    feed.lot("b", "parag", "2025-05-01", 50, 22)
    import_feed(factory, feed.body())
    assert import_feed(factory, feed.body()).added == 0  # nothing changed: nothing new

    feed.lot("a", "parag", "2025-04-01", 120, 20)  # changed in FM
    del feed.lots["b"]  # deleted in FM
    feed.lot("c", "nifty", "2025-06-01", 10, 200)
    row = import_feed(factory, feed.body())

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


def test_purchases_entered_in_friday_stay(own_lot, feed, factory, funds) -> None:
    feed.lot("a", "parag", "2025-04-01", 100, 20)
    import_feed(factory, feed.body())
    row = import_feed(factory, feed.body())

    with session_scope(factory) as session:
        sources = session.scalars(select(Lot.source).order_by(Lot.buy_date)).all()
    assert sources == ["fm", None]
    assert json.loads(row.warnings) == [
        "Parag Parikh Flexi Cap Fund also has purchases or SIPs entered in Friday; "
        "they count alongside FM's."
    ]


def test_what_cant_be_imported_is_listed(feed, factory, funds) -> None:
    feed.lot("a", "parag", "2025-04-01", 100, 20)
    feed.lot("ghost", "ghost", "2025-04-01", 10, 10)
    feed.lot("usd", "nifty", "2025-04-01", 10, 10, currency="USD")
    feed.lot("odd", "nifty", "2025-04-02", 10, 10)["remaining_units"] = 4

    row = import_feed(factory, feed.body())

    assert row.lots == 2
    assert json.loads(row.warnings) == [
        "A purchase of UTI nifty is in USD; it was left out.",
        "FM shows 4 units left in the 02 Apr 2025 UTI nifty purchase; its sales leave 10. "
        "Friday uses its sales.",
        "AMFI 999999 (Closed fund) isn't in the fund list; its purchases were left out.",
    ]


@pytest.mark.parametrize(
    ("body", "message"),
    [
        (b"not json", "it isn't JSON"),
        (b'{"format": "something"}', "it isn't an FM lots feed"),
        (b'{"format": "fm-lots", "version": 2, "lots": []}', "FM sent version 2"),
    ],
)
def test_a_feed_that_cant_be_read_is_logged_and_refused(body, message, factory) -> None:
    with pytest.raises(FmFeedError, match=message):
        import_feed(factory, body)
    with session_scope(factory) as session:
        logged = session.scalars(select(FmImport)).one()
        assert logged.status == "failed"
        assert message in logged.message


def test_a_removed_field_is_reported(feed) -> None:
    del feed.lot("a", "parag", "2025-04-01", 100, 20)["unit_price"]
    with pytest.raises(FmFeedError, match="FM's lots have changed: 'unit_price'"):
        read_feed(feed.body())


def buckets_of(factory: sessionmaker[Session]) -> dict[str, str | None]:
    """FM lot id → the name of the Friday bucket it's in."""
    with session_scope(factory) as session:
        lots = session.scalars(select(Lot).where(Lot.source == "fm")).all()
        return {lot.source_id: lot.bucket.name if lot.bucket else None for lot in lots}


def test_purchases_land_in_the_buckets_fm_put_them_in(feed, factory, funds) -> None:
    with session_scope(factory) as session:
        create_bucket(session, BucketInput("retirement"))  # made in Friday first
        create_bucket(session, BucketInput("House", paper=True))
    feed.lot("a", "parag", "2025-04-01", 10, 20, bucket=("b1", "Retirement"))
    feed.lot("b", "nifty", "2025-05-08", 10, 20, bucket=("b2", "House"))
    feed.lot("c", "nifty", "2025-06-08", 10, 20)

    import_feed(factory, feed.body())

    # A real bucket of the same name is FM's from now on; a paper one is never.
    assert buckets_of(factory) == {"a": "Retirement", "b": "House (FM)", "c": None}

    # Renamed in FM: the same bucket, renamed. Moved in FM: moved here.
    feed.lots["a"]["bucket"] = {"id": "b1", "name": "Pension"}
    feed.lots["c"]["bucket"] = {"id": "b1", "name": "Pension"}
    import_feed(factory, feed.body())

    assert buckets_of(factory) == {"a": "Pension", "b": "House (FM)", "c": "Pension"}
    with session_scope(factory) as session:
        names = sorted(session.scalars(select(Bucket.name)))
    assert names == ["House", "House (FM)", "Pension"]
