"""Funds, buckets or models side by side: returns, risk and consistency over the dates they
share."""

from collections.abc import Callable
from datetime import date
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy.orm import Session

from friday.api.deps import SessionDep
from friday.api.routes.models import Rebalance
from friday.api.schemas import BucketRef, FundRef, ModelRef
from friday.core.buckets.models import Bucket
from friday.core.compare.schemas import (
    BucketComparison,
    Compared,
    ComparedBucket,
    Comparison,
)
from friday.core.compare.service import (
    CompareError,
    compare_buckets,
    compare_funds,
    compare_models,
)
from friday.core.instruments.models import Instrument
from friday.core.models.models import Model

router = APIRouter(tags=["compare"])

Ids = Annotated[list[int], Query()]


class ComparedFundOut(Compared):
    fund: FundRef


class FundComparisonOut(Comparison):
    items: list[ComparedFundOut]
    benchmark: ComparedFundOut | None


class ComparedBucketOut(ComparedBucket):
    bucket: BucketRef
    model: ModelRef | None


class BucketComparisonOut(BucketComparison):
    items: list[ComparedBucketOut]
    benchmark: ComparedFundOut | None


class ComparedModelOut(Compared):
    model: ModelRef
    rebalance: Rebalance


class ModelComparisonOut(Comparison):
    items: list[ComparedModelOut]
    benchmark: ComparedFundOut | None


def _run[T: Comparison](make: Callable[[], T]) -> T:
    try:
        return make()
    except LookupError as error:
        raise HTTPException(404, str(error)) from None
    except CompareError as error:
        raise HTTPException(422, str(error)) from None


def _fund(session: Session, item: Compared) -> ComparedFundOut:
    instrument = session.get(Instrument, item.id)
    return ComparedFundOut(
        **item.model_dump(), fund=FundRef.model_validate(instrument, from_attributes=True)
    )


def _benchmark(session: Session, result: Comparison) -> ComparedFundOut | None:
    return _fund(session, result.benchmark) if result.benchmark else None


@router.get("/compare/funds", operation_id="compareFunds")
def funds(
    session: SessionDep,
    ids: Ids,
    benchmark_id: int | None = None,
    start: date | None = None,
    end: date | None = None,
    rolling_years: int = 3,
) -> FundComparisonOut:
    """Compare funds over the dates they all have, or from ``start`` for the funds that go
    back that far, against ``benchmark_id`` or the default benchmark."""
    result = _run(
        lambda: compare_funds(
            session,
            ids,
            benchmark_id=benchmark_id,
            start=start,
            end=end,
            rolling_years=rolling_years,
        )
    )
    return FundComparisonOut(
        **result.model_dump(exclude={"items", "benchmark"}),
        items=[_fund(session, item) for item in result.items],
        benchmark=_benchmark(session, result),
    )


@router.get("/compare/buckets", operation_id="compareBuckets")
def buckets(
    session: SessionDep,
    ids: Ids,
    benchmark_id: int | None = None,
    start: date | None = None,
    end: date | None = None,
    rolling_years: int = 3,
) -> BucketComparisonOut:
    """Compare buckets on their time-weighted growth, with what the money in each made."""
    result = _run(
        lambda: compare_buckets(
            session,
            ids,
            benchmark_id=benchmark_id,
            start=start,
            end=end,
            rolling_years=rolling_years,
        )
    )

    def out(item: ComparedBucket) -> ComparedBucketOut:
        bucket = session.get(Bucket, item.id)
        assert bucket is not None
        return ComparedBucketOut(
            **item.model_dump(),
            bucket=BucketRef(id=bucket.id, name=bucket.name, paper=bucket.paper),
            model=ModelRef(id=bucket.model.id, name=bucket.model.name) if bucket.model else None,
        )

    return BucketComparisonOut(
        **result.model_dump(exclude={"items", "benchmark"}),
        items=[out(item) for item in result.items],
        benchmark=_benchmark(session, result),
    )


@router.get("/compare/models", operation_id="compareModels")
def models(
    session: SessionDep,
    ids: Ids,
    benchmark_id: int | None = None,
    start: date | None = None,
    end: date | None = None,
    rolling_years: int = 3,
) -> ModelComparisonOut:
    """Compare models as if each were one fund: a lump sum split by its weights and
    rebalanced as it says."""
    result = _run(
        lambda: compare_models(
            session,
            ids,
            benchmark_id=benchmark_id,
            start=start,
            end=end,
            rolling_years=rolling_years,
        )
    )

    def out(item: Compared) -> ComparedModelOut:
        model = session.get(Model, item.id)
        assert model is not None
        return ComparedModelOut(
            **item.model_dump(),
            model=ModelRef(id=model.id, name=model.name),
            rebalance=model.rebalance,
        )

    return ModelComparisonOut(
        **result.model_dump(exclude={"items", "benchmark"}),
        items=[out(item) for item in result.items],
        benchmark=_benchmark(session, result),
    )
