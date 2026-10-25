"""Buckets: target splits of funds (T1-13, D-047)."""

from datetime import date
from typing import Literal

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from friday.api.deps import SessionDep
from friday.api.schemas import CoverageOut, FundRef
from friday.core.buckets.models import Bucket
from friday.core.buckets.service import (
    BucketInput,
    DuplicateBucket,
    InvalidBucket,
    create_bucket,
    default_benchmark,
    delete_bucket,
    list_buckets,
    update_bucket,
)
from friday.core.instruments.models import Instrument
from friday.core.navs.service import Coverage, coverage
from friday.core.schema_types import Percent, UtcDatetime

router = APIRouter(prefix="/buckets", tags=["buckets"])

Rebalance = Literal["none", "monthly", "quarterly", "yearly"]


class FundWithCoverage(BaseModel):
    fund: FundRef
    coverage: CoverageOut


class BucketFundOut(FundWithCoverage):
    weight: Percent


class BucketOut(BaseModel):
    id: int
    name: str
    description: str | None
    rebalance: Rebalance
    benchmark: FundWithCoverage | None
    funds: list[BucketFundOut]
    common_start: date | None
    """First date every fund in the bucket has a NAV: the earliest a backtest can start."""
    created_at: UtcDatetime
    updated_at: UtcDatetime


class BucketFundIn(BaseModel):
    instrument_id: int
    weight: Percent


class BucketIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=500)
    rebalance: Rebalance = "none"
    benchmark_id: int | None = None
    funds: list[BucketFundIn] = Field(min_length=1)


def _input(payload: BucketIn) -> BucketInput:
    return BucketInput(
        name=payload.name,
        description=payload.description,
        rebalance=payload.rebalance,
        benchmark_id=payload.benchmark_id,
        funds=[(fund.instrument_id, fund.weight) for fund in payload.funds],
    )


def _coverage(value: Coverage) -> CoverageOut:
    return CoverageOut(first=value.first, last=value.last, count=value.count)


def _ref(instrument: Instrument) -> FundRef:
    return FundRef.model_validate(instrument, from_attributes=True)


def _out(session: Session, bucket: Bucket) -> BucketOut:
    ids = [member.instrument_id for member in bucket.funds]
    covered = coverage(session, ids + ([bucket.benchmark_id] if bucket.benchmark_id else []))
    firsts = [covered[i].first for i in ids]
    return BucketOut(
        id=bucket.id,
        name=bucket.name,
        description=bucket.description,
        rebalance=bucket.rebalance,
        benchmark=FundWithCoverage(
            fund=_ref(bucket.benchmark), coverage=_coverage(covered[bucket.benchmark.id])
        )
        if bucket.benchmark
        else None,
        funds=[
            BucketFundOut(
                fund=_ref(member.instrument),
                weight=member.weight_pct,
                coverage=_coverage(covered[member.instrument_id]),
            )
            for member in bucket.funds
        ],
        common_start=max(firsts) if firsts and all(firsts) else None,
        created_at=bucket.created_at,
        updated_at=bucket.updated_at,
    )


def _get(session: Session, bucket_id: int) -> Bucket:
    bucket = session.get(Bucket, bucket_id)
    if bucket is None:
        raise HTTPException(404, f"No bucket with id {bucket_id}.")
    return bucket


def _sentence(error: Exception) -> str:
    text = str(error)
    return text[:1].upper() + text[1:] + "."


def _save(session: Session, action, *args) -> Bucket:
    try:
        return action(session, *args)
    except InvalidBucket as error:
        raise HTTPException(422, _sentence(error)) from None
    except DuplicateBucket as error:
        raise HTTPException(409, _sentence(error)) from None


@router.get("", operation_id="listBuckets")
def list_all(session: SessionDep) -> list[BucketOut]:
    return [_out(session, bucket) for bucket in list_buckets(session)]


@router.get("/default-benchmark", operation_id="getDefaultBenchmark")
def get_default_benchmark(session: SessionDep) -> FundRef | None:
    """The Nifty 50 index fund new buckets are compared with (D-043), if the fund list has it."""
    instrument = default_benchmark(session)
    return _ref(instrument) if instrument else None


@router.post("", status_code=201, operation_id="createBucket")
def create(session: SessionDep, payload: BucketIn) -> BucketOut:
    """Weights must add up to exactly 100. Every fund and the benchmark become tracked."""
    return _out(session, _save(session, create_bucket, _input(payload)))


@router.get("/{bucket_id}", operation_id="getBucket")
def get(session: SessionDep, bucket_id: int) -> BucketOut:
    return _out(session, _get(session, bucket_id))


@router.put("/{bucket_id}", operation_id="updateBucket")
def update(session: SessionDep, bucket_id: int, payload: BucketIn) -> BucketOut:
    bucket = _get(session, bucket_id)
    return _out(session, _save(session, update_bucket, bucket, _input(payload)))


@router.delete("/{bucket_id}", status_code=204, operation_id="deleteBucket")
def delete(session: SessionDep, bucket_id: int) -> Response:
    """Delete a bucket and its saved backtests. Its funds' NAVs stay."""
    delete_bucket(session, _get(session, bucket_id))
    return Response(status_code=204)
