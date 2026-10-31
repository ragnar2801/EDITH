"""Creating and changing buckets (D-047).

Weights are exact percentages that must add up to exactly 100: a split that only looks
like 100% is refused rather than quietly normalised. Only AMFI schemes can be in a bucket
or be its benchmark. Everything in a bucket is tracked for NAVs (D-046).
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from friday.core.buckets.models import REBALANCE, Bucket, BucketFund
from friday.core.instruments.models import Instrument

HUNDRED = Decimal(100)

DEFAULT_BENCHMARK = "120716"
"""UTI Nifty 50 Index Fund – Direct Plan – Growth: the Nifty 50, dividends included (D-043)."""


class InvalidBucket(ValueError):
    pass


class DuplicateBucket(ValueError):
    pass


@dataclass(frozen=True)
class BucketInput:
    name: str
    funds: list[tuple[int, Decimal]]
    rebalance: str = "none"
    benchmark_id: int | None = None
    description: str | None = None


def default_benchmark(session: Session) -> Instrument | None:
    return session.scalars(
        select(Instrument).where(Instrument.amfi_code == DEFAULT_BENCHMARK)
    ).first()


def _fund(session: Session, instrument_id: int, role: str) -> Instrument:
    instrument = session.get(Instrument, instrument_id)
    if instrument is None:
        raise InvalidBucket(f"{role}: no instrument with id {instrument_id}")
    if not instrument.amfi_code:
        raise InvalidBucket(f"{role}: {instrument.name} is not a mutual fund scheme")
    return instrument


def check_split(session: Session, funds: list[tuple[int, Decimal]]) -> list[Instrument]:
    """The funds of a split, if it's one a bucket could have (also a backtest's, D-075)."""
    if not funds:
        raise InvalidBucket("add at least one fund")
    ids = [instrument_id for instrument_id, _ in funds]
    if len(set(ids)) != len(ids):
        raise InvalidBucket("a fund is listed twice")
    instruments = []
    for instrument_id, weight in funds:
        fund = _fund(session, instrument_id, "fund")
        if weight <= 0 or weight > HUNDRED:
            raise InvalidBucket(f"{fund.name}: weight must be more than 0 and at most 100")
        instruments.append(fund)
    total = sum((weight for _, weight in funds), Decimal(0))
    if total != HUNDRED:
        raise InvalidBucket(f"weights must add up to 100, not {total.normalize():f}")
    return instruments


def _validate(session: Session, data: BucketInput, bucket_id: int | None) -> str:
    name = " ".join(data.name.split())
    if not name:
        raise InvalidBucket("give the bucket a name")
    if data.rebalance not in REBALANCE:
        raise InvalidBucket(f"rebalance must be one of {', '.join(REBALANCE)}")
    check_split(session, data.funds)
    if data.benchmark_id is not None:
        _fund(session, data.benchmark_id, "benchmark")

    clash = session.scalars(select(Bucket).where(Bucket.name == name)).first()
    if clash is not None and clash.id != bucket_id:
        raise DuplicateBucket(f"there is already a bucket called {name}")
    return name


def _apply(bucket: Bucket, data: BucketInput, name: str, now: datetime) -> None:
    bucket.name = name
    bucket.description = (data.description or "").strip() or None
    bucket.rebalance = data.rebalance
    bucket.benchmark_id = data.benchmark_id
    bucket.updated_at = now
    weights = dict(data.funds)
    positions = {instrument_id: i for i, (instrument_id, _) in enumerate(data.funds)}
    kept = []
    for member in bucket.funds:
        if member.instrument_id in weights:
            member.weight_pct = weights.pop(member.instrument_id)
            member.position = positions[member.instrument_id]
            kept.append(member)
    bucket.funds = kept + [
        BucketFund(
            instrument_id=instrument_id, weight_pct=weight, position=positions[instrument_id]
        )
        for instrument_id, weight in weights.items()
    ]


def create_bucket(session: Session, data: BucketInput) -> Bucket:
    name = _validate(session, data, None)
    now = datetime.now(UTC)
    bucket = Bucket(created_at=now)
    _apply(bucket, data, name, now)
    session.add(bucket)
    session.flush()
    return bucket


def update_bucket(session: Session, bucket: Bucket, data: BucketInput) -> Bucket:
    name = _validate(session, data, bucket.id)
    _apply(bucket, data, name, datetime.now(UTC))
    session.flush()
    session.refresh(bucket)
    return bucket


def delete_bucket(session: Session, bucket: Bucket) -> None:
    session.delete(bucket)
    session.flush()


def list_buckets(session: Session) -> list[Bucket]:
    return list(session.scalars(select(Bucket).order_by(Bucket.name)))


def bucket_reasons(session: Session) -> dict[int, list[str]]:
    """Every fund a bucket uses, with why: ``bucket <name>`` or ``benchmark of <name>``."""
    reasons: dict[int, list[str]] = {}
    for bucket in list_buckets(session):
        for member in bucket.funds:
            reasons.setdefault(member.instrument_id, []).append(f"bucket {bucket.name}")
        if bucket.benchmark_id is not None:
            reasons.setdefault(bucket.benchmark_id, []).append(f"benchmark of {bucket.name}")
    return reasons
