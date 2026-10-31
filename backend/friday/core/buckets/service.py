"""Creating, changing and deleting buckets, and the buckets an FM sync brings.

A bucket's model can change at any time: it only steers new money. Whether a bucket is
paper is set while it is empty, so real and pretend purchases never mix. Buckets from FM
are named there; deleting one leaves its purchases in no bucket until FM sends it again.
Deleting a paper bucket deletes its purchases and SIPs with it.
"""

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

from friday.core.buckets.models import Bucket
from friday.core.holdings.models import Lot, LotSale, Sip
from friday.core.models.models import Model


class InvalidBucket(ValueError):
    pass


class DuplicateBucket(ValueError):
    pass


@dataclass(frozen=True)
class BucketInput:
    name: str
    model_id: int | None = None
    paper: bool = False


def _now() -> datetime:
    return datetime.now(UTC)


def _clean(name: str) -> str:
    return " ".join(name.split())


def _taken(session: Session, name: str, bucket_id: int | None) -> bool:
    clash = session.scalars(select(Bucket).where(func.lower(Bucket.name) == name.lower())).first()
    return clash is not None and clash.id != bucket_id


def has_purchases(session: Session, bucket: Bucket) -> bool:
    lots = select(Lot.id).where(Lot.bucket_id == bucket.id)
    sips = select(Sip.id).where(Sip.bucket_id == bucket.id)
    return session.scalar(select(lots.union(sips).exists())) or False


def _validate(session: Session, data: BucketInput, bucket: Bucket | None) -> str:
    name = _clean(data.name)
    if not name:
        raise InvalidBucket("give the bucket a name")
    if data.model_id is not None and session.get(Model, data.model_id) is None:
        raise InvalidBucket(f"no model with id {data.model_id}")
    if bucket is not None and bucket.fm_id is not None:
        if name != bucket.name:
            raise InvalidBucket("this bucket comes from FM; rename it there")
        if data.paper:
            raise InvalidBucket("a bucket from FM holds real purchases; it can't be paper")
    if bucket is not None and data.paper != bucket.paper and has_purchases(session, bucket):
        raise InvalidBucket(
            "a bucket with purchases can't switch between paper and real; make a new one"
        )
    if _taken(session, name, bucket.id if bucket else None):
        raise DuplicateBucket(f"there is already a bucket called {name}")
    return name


def create_bucket(session: Session, data: BucketInput) -> Bucket:
    name = _validate(session, data, None)
    now = _now()
    bucket = Bucket(
        name=name, paper=data.paper, model_id=data.model_id, created_at=now, updated_at=now
    )
    session.add(bucket)
    session.flush()
    return bucket


def update_bucket(session: Session, bucket: Bucket, data: BucketInput) -> Bucket:
    bucket.name = _validate(session, data, bucket)
    bucket.model_id = data.model_id
    bucket.paper = data.paper
    bucket.updated_at = _now()
    session.flush()
    session.refresh(bucket)
    return bucket


def delete_bucket(session: Session, bucket: Bucket) -> None:
    """Delete a bucket. A paper bucket's purchases, sales and SIPs go with it; a real
    bucket's purchases and SIPs stay, in no bucket."""
    lots = select(Lot.id).where(Lot.bucket_id == bucket.id)
    if bucket.paper:
        session.execute(delete(LotSale).where(LotSale.lot_id.in_(lots)))
        session.execute(delete(Lot).where(Lot.bucket_id == bucket.id))
        session.execute(delete(Sip).where(Sip.bucket_id == bucket.id))
    else:
        session.execute(update(Lot).where(Lot.bucket_id == bucket.id).values(bucket_id=None))
        session.execute(update(Sip).where(Sip.bucket_id == bucket.id).values(bucket_id=None))
    session.delete(bucket)
    session.flush()
    session.expire_all()


def list_buckets(session: Session) -> list[Bucket]:
    """Real buckets first, then paper ones, each by name."""
    return list(session.scalars(select(Bucket).order_by(Bucket.paper, Bucket.name)))


def fm_bucket(session: Session, fm_id: str, name: str) -> Bucket:
    """The bucket for one of FM's: the one it made before, else a real bucket of the same name
    not yet tied to FM, else a new one. Takes FM's name when that is free."""
    name = _clean(name) or "FM bucket"
    bucket = session.scalars(select(Bucket).where(Bucket.fm_id == fm_id)).first()
    if bucket is None:
        bucket = session.scalars(
            select(Bucket).where(
                func.lower(Bucket.name) == name.lower(),
                Bucket.fm_id.is_(None),
                Bucket.paper.is_(False),
            )
        ).first()
        if bucket is not None:
            bucket.fm_id = fm_id
    if bucket is None:
        now = _now()
        bucket = Bucket(name=_free(session, name), fm_id=fm_id, created_at=now, updated_at=now)
        session.add(bucket)
    elif bucket.name != name and not _taken(session, name, bucket.id):
        bucket.name = name
        bucket.updated_at = _now()
    session.flush()
    return bucket


def _free(session: Session, name: str) -> str:
    """``name``, or ``name (FM)``, ``name (FM 2)``, … if a bucket already has it."""
    candidate, number = name, 1
    while _taken(session, candidate, None):
        candidate = f"{name} (FM)" if number == 1 else f"{name} (FM {number})"
        number += 1
    return candidate
