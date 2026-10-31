"""Buckets: money set aside for a goal, real or paper, each following a model."""

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from friday.api.deps import SessionDep
from friday.api.routes.models import _sentence
from friday.api.schemas import BucketRef, ModelRef
from friday.core.buckets.models import Bucket
from friday.core.buckets.service import (
    BucketInput,
    DuplicateBucket,
    InvalidBucket,
    create_bucket,
    delete_bucket,
    list_buckets,
    update_bucket,
)
from friday.core.holdings.models import Lot
from friday.core.portfolio.service import portfolio
from friday.core.schema_types import Amount

router = APIRouter(prefix="/buckets", tags=["buckets"])


class BucketOut(BaseModel):
    id: int
    name: str
    paper: bool
    """Pretend purchases at real NAVs, kept out of the portfolio's totals."""
    from_fm: bool
    """Made by an FM sync: named in FM, and its FM purchases are changed there."""
    model: ModelRef | None
    purchases: int
    """Purchases in the bucket, SIP instalments included."""
    cost: Amount
    """What the units still held cost."""
    value: Amount | None
    """At each fund's latest NAV; blank when the bucket holds nothing with a NAV."""
    gain: Amount | None
    ahead_of_model: Amount | None
    """Gain − the gain of the same money split by the model's weights on the same dates."""


class BucketIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    model_id: int | None = None
    paper: bool = False


def ref(bucket: Bucket) -> BucketRef:
    return BucketRef(id=bucket.id, name=bucket.name, paper=bucket.paper)


def _out(session: Session, bucket: Bucket) -> BucketOut:
    view = portfolio(session, bucket)
    purchases = session.scalar(
        select(func.count(Lot.id)).where(Lot.bucket_id == bucket.id, Lot.skipped.is_(False))
    )
    model = bucket.model
    return BucketOut(
        id=bucket.id,
        name=bucket.name,
        paper=bucket.paper,
        from_fm=bucket.fm_id is not None,
        model=ModelRef(id=model.id, name=model.name) if model else None,
        purchases=purchases or 0,
        cost=view.cost,
        value=view.returns.value if view.returns else None,
        gain=view.returns.gain if view.returns else None,
        ahead_of_model=view.ahead_of_model,
    )


def get_bucket(session: Session, bucket_id: int) -> Bucket:
    bucket = session.get(Bucket, bucket_id)
    if bucket is None:
        raise HTTPException(404, f"No bucket with id {bucket_id}.")
    return bucket


def _save(session: Session, action, *args) -> Bucket:
    try:
        return action(session, *args)
    except InvalidBucket as error:
        raise HTTPException(422, _sentence(error)) from None
    except DuplicateBucket as error:
        raise HTTPException(409, _sentence(error)) from None


def _input(payload: BucketIn) -> BucketInput:
    return BucketInput(name=payload.name, model_id=payload.model_id, paper=payload.paper)


@router.get("", operation_id="listBuckets")
def list_all(session: SessionDep) -> list[BucketOut]:
    """Real buckets first, then paper ones, with what each holds."""
    return [_out(session, bucket) for bucket in list_buckets(session)]


@router.post("", status_code=201, operation_id="createBucket")
def create(session: SessionDep, payload: BucketIn) -> BucketOut:
    return _out(session, _save(session, create_bucket, _input(payload)))


@router.put("/{bucket_id}", operation_id="updateBucket")
def update(session: SessionDep, bucket_id: int, payload: BucketIn) -> BucketOut:
    """Rename it or change its model. Paper or real changes only while it's empty."""
    bucket = get_bucket(session, bucket_id)
    return _out(session, _save(session, update_bucket, bucket, _input(payload)))


@router.delete("/{bucket_id}", status_code=204, operation_id="deleteBucket")
def delete(session: SessionDep, bucket_id: int) -> Response:
    """Delete a bucket. A paper bucket's purchases and SIPs go with it; a real bucket's stay,
    in no bucket."""
    delete_bucket(session, get_bucket(session, bucket_id))
    return Response(status_code=204)
