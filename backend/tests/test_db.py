from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy import Column, Integer, MetaData, Table, insert, select, text
from sqlalchemy.exc import StatementError

from friday.config import Settings
from friday.core.db import make_engine, upgrade_database
from friday.core.types import DecimalText, UtcDateTime

metadata = MetaData()
sample = Table(
    "sample",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("amount", DecimalText(scale=2)),
    Column("units", DecimalText(scale=8)),
    Column("at", UtcDateTime()),
)


@pytest.fixture
def engine(settings: Settings):
    engine = make_engine(settings)
    metadata.create_all(engine)
    yield engine
    engine.dispose()


def test_pragmas_are_applied(engine) -> None:
    with engine.connect() as connection:
        assert connection.execute(text("PRAGMA journal_mode")).scalar() == "wal"
        assert connection.execute(text("PRAGMA foreign_keys")).scalar() == 1
        assert connection.execute(text("PRAGMA busy_timeout")).scalar() == 5000


def test_decimals_and_timestamps_survive_the_database(engine) -> None:
    ist = timezone(timedelta(hours=5, minutes=30))
    with engine.begin() as connection:
        connection.execute(
            insert(sample).values(
                amount=Decimal("1234567.89"),
                units=Decimal("0.12345678"),
                at=datetime(2026, 10, 24, 9, 30, tzinfo=ist),
            )
        )
        row = connection.execute(select(sample)).one()
        stored = connection.execute(text("SELECT amount, at FROM sample")).one()

    assert row.amount == Decimal("1234567.89")
    assert row.units == Decimal("0.12345678")
    assert row.at == datetime(2026, 10, 24, 4, 0, tzinfo=UTC)
    assert stored.amount == "1234567.89"  # exact text, not a float
    assert stored.at == "2026-10-24T04:00:00.000000Z"


def test_float_is_refused(engine) -> None:
    with pytest.raises(StatementError, match="float is not allowed"), engine.begin() as connection:
        connection.execute(insert(sample).values(amount=0.1))


def test_extra_decimal_places_are_refused(engine) -> None:
    refused = pytest.raises(StatementError, match="more than 2 decimal places")
    with refused, engine.begin() as connection:
        connection.execute(insert(sample).values(amount=Decimal("1.005")))


def test_trailing_zeros_do_not_count_as_extra_places(engine) -> None:
    with engine.begin() as connection:
        connection.execute(insert(sample).values(amount=Decimal("1.5000")))


def test_naive_datetime_is_refused(engine) -> None:
    with pytest.raises(StatementError, match="naive datetime"), engine.begin() as connection:
        connection.execute(insert(sample).values(at=datetime(2026, 1, 1)))  # noqa: DTZ001


def test_migrations_run_and_are_repeatable(settings: Settings) -> None:
    upgrade_database(settings)
    upgrade_database(settings)

    engine = make_engine(settings)
    with engine.connect() as connection:
        version = connection.execute(text("SELECT version_num FROM alembic_version")).scalar()
    engine.dispose()
    assert version == "0002"
