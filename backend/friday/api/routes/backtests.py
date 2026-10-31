"""Backtests of a bucket: run, save, load, delete, figures for a window, and two runs
compared, and every split of a bucket searched."""

from datetime import date

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, Field, TypeAdapter
from sqlalchemy.orm import Session

from friday.api.deps import SessionDep
from friday.api.routes.buckets import _sentence
from friday.core.backtest.engine import EngineError
from friday.core.backtest.models import BacktestRun
from friday.core.backtest.schemas import (
    BacktestParams,
    BacktestResult,
    ComparisonOut,
    IntervalOut,
    OptimiseOut,
    SearchParams,
    SearchSettings,
    Strategy,
)
from friday.core.backtest.service import (
    compare_runs,
    optimise,
    run_backtest,
    run_interval,
    saved_runs,
    store_run,
)
from friday.core.buckets.models import Bucket
from friday.core.schema_types import UtcDatetime

router = APIRouter(tags=["backtests"])

_params = TypeAdapter(BacktestParams)


class BacktestIn(BaseModel):
    bucket_id: int
    params: BacktestParams
    save: bool = False
    name: str | None = Field(default=None, max_length=120)


class OptimiseIn(SearchSettings):
    bucket_id: int
    params: SearchParams


class BacktestRunSummary(BaseModel):
    id: int
    bucket_id: int
    strategy: Strategy
    saved: bool
    name: str | None
    created_at: UtcDatetime
    params: BacktestParams


class BacktestRunOut(BacktestRunSummary):
    bucket_name: str
    result: BacktestResult


class RunUpdate(BaseModel):
    saved: bool
    name: str | None = Field(default=None, max_length=120)


def _bucket(session: Session, bucket_id: int) -> Bucket:
    bucket = session.get(Bucket, bucket_id)
    if bucket is None:
        raise HTTPException(404, f"No bucket with id {bucket_id}.")
    return bucket


def _run(session: Session, run_id: int) -> BacktestRun:
    run = session.get(BacktestRun, run_id)
    if run is None:
        raise HTTPException(404, f"No backtest run with id {run_id}.")
    return run


def _summary(run: BacktestRun) -> BacktestRunSummary:
    return BacktestRunSummary(
        id=run.id,
        bucket_id=run.bucket_id,
        strategy=run.strategy,
        saved=run.saved,
        name=run.name,
        created_at=run.created_at,
        params=_params.validate_json(run.params),
    )


def _out(session: Session, run: BacktestRun) -> BacktestRunOut:
    return BacktestRunOut(
        **_summary(run).model_dump(),
        bucket_name=_bucket(session, run.bucket_id).name,
        result=BacktestResult.model_validate_json(run.result),
    )


@router.post("/backtests", operation_id="runBacktest")
def run(session: SessionDep, payload: BacktestIn) -> BacktestRunOut:
    """Run a backtest on the bucket's stored NAVs and keep it; ``save`` keeps it for good."""
    bucket = _bucket(session, payload.bucket_id)
    try:
        result = run_backtest(session, bucket, payload.params)
    except EngineError as error:
        raise HTTPException(422, _sentence(error)) from None
    stored = store_run(
        session, bucket, payload.params, result, saved=payload.save, name=payload.name
    )
    return _out(session, stored)


@router.post("/backtests/optimise", operation_id="optimiseSplit")
def optimise_split(session: SessionDep, payload: OptimiseIn) -> OptimiseOut:
    """Try every split of the bucket's funds and rank them; nothing is stored."""
    bucket = _bucket(session, payload.bucket_id)
    try:
        return optimise(session, bucket, payload.params, payload)
    except EngineError as error:
        raise HTTPException(422, _sentence(error)) from None


@router.get("/buckets/{bucket_id}/backtests", operation_id="listSavedBacktests")
def list_saved(session: SessionDep, bucket_id: int) -> list[BacktestRunSummary]:
    """Saved runs of a bucket, newest first."""
    _bucket(session, bucket_id)
    return [_summary(run) for run in saved_runs(session, bucket_id)]


@router.get("/backtests/{run_id}", operation_id="getBacktest")
def get(session: SessionDep, run_id: int) -> BacktestRunOut:
    return _out(session, _run(session, run_id))


@router.patch("/backtests/{run_id}", operation_id="updateBacktest")
def update(session: SessionDep, run_id: int, payload: RunUpdate) -> BacktestRunSummary:
    """Save a run (with an optional name), or unsave it."""
    run = _run(session, run_id)
    run.saved = payload.saved
    run.name = (payload.name or "").strip() or None
    session.flush()
    return _summary(run)


@router.delete("/backtests/{run_id}", status_code=204, operation_id="deleteBacktest")
def delete(session: SessionDep, run_id: int) -> Response:
    session.delete(_run(session, run_id))
    return Response(status_code=204)


@router.get("/backtests/{run_id}/interval", operation_id="getBacktestInterval")
def interval(
    session: SessionDep, run_id: int, start: date | None = None, end: date | None = None
) -> IntervalOut:
    """Return, drawdown and money in and out for a window of a run."""
    result = BacktestResult.model_validate_json(_run(session, run_id).result)
    window = run_interval(result, start, end)
    if window is None:
        raise HTTPException(422, "Pick a window with at least two dates in the run.")
    return window


@router.get("/backtests/{run_id}/compare", operation_id="compareBacktests")
def compare(session: SessionDep, run_id: int, against: int) -> ComparisonOut:
    """This run less an earlier one: final value, ratios and the weights that changed."""
    run, earlier = _run(session, run_id), _run(session, against)
    return compare_runs(
        _params.validate_json(run.params),
        BacktestResult.model_validate_json(run.result),
        earlier.id,
        _params.validate_json(earlier.params),
        BacktestResult.model_validate_json(earlier.result),
    )
