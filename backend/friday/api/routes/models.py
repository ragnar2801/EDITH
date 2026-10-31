"""Models: target splits of funds."""

from datetime import date
from typing import Literal

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from friday.api.deps import SessionDep
from friday.api.schemas import CoverageOut, FundRef
from friday.core.instruments.models import Instrument
from friday.core.models.models import Model
from friday.core.models.service import (
    DuplicateModel,
    InvalidModel,
    ModelInput,
    create_model,
    default_benchmark,
    delete_model,
    duplicate_model,
    list_models,
    update_model,
)
from friday.core.navs.service import Coverage, coverage
from friday.core.schema_types import Percent, UtcDatetime

router = APIRouter(prefix="/models", tags=["models"])

Rebalance = Literal["none", "monthly", "quarterly", "yearly"]


class FundWithCoverage(BaseModel):
    fund: FundRef
    coverage: CoverageOut


class ModelFundOut(FundWithCoverage):
    weight: Percent


class ModelOut(BaseModel):
    id: int
    name: str
    description: str | None
    rebalance: Rebalance
    benchmark: FundWithCoverage | None
    funds: list[ModelFundOut]
    common_start: date | None
    """First date every fund in the model has a NAV: the earliest a backtest can start."""
    created_at: UtcDatetime
    updated_at: UtcDatetime


class ModelFundIn(BaseModel):
    instrument_id: int
    weight: Percent


class ModelIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=500)
    rebalance: Rebalance = "none"
    benchmark_id: int | None = None
    funds: list[ModelFundIn] = Field(min_length=1)


def _input(payload: ModelIn) -> ModelInput:
    return ModelInput(
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


def _out(session: Session, model: Model) -> ModelOut:
    ids = [member.instrument_id for member in model.funds]
    covered = coverage(session, ids + ([model.benchmark_id] if model.benchmark_id else []))
    firsts = [covered[i].first for i in ids]
    return ModelOut(
        id=model.id,
        name=model.name,
        description=model.description,
        rebalance=model.rebalance,
        benchmark=FundWithCoverage(
            fund=_ref(model.benchmark), coverage=_coverage(covered[model.benchmark.id])
        )
        if model.benchmark
        else None,
        funds=[
            ModelFundOut(
                fund=_ref(member.instrument),
                weight=member.weight_pct,
                coverage=_coverage(covered[member.instrument_id]),
            )
            for member in model.funds
        ],
        common_start=max(firsts) if firsts and all(firsts) else None,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _get(session: Session, model_id: int) -> Model:
    model = session.get(Model, model_id)
    if model is None:
        raise HTTPException(404, f"No model with id {model_id}.")
    return model


def _sentence(error: Exception) -> str:
    """An error message as a sentence: first letter up, full stop."""
    text = str(error)
    return text[:1].upper() + text[1:] + "."


def _save(session: Session, action, *args) -> Model:
    try:
        return action(session, *args)
    except InvalidModel as error:
        raise HTTPException(422, _sentence(error)) from None
    except DuplicateModel as error:
        raise HTTPException(409, _sentence(error)) from None


@router.get("", operation_id="listModels")
def list_all(session: SessionDep) -> list[ModelOut]:
    return [_out(session, model) for model in list_models(session)]


@router.get("/default-benchmark", operation_id="getDefaultBenchmark")
def get_default_benchmark(session: SessionDep) -> FundRef | None:
    """The Nifty 50 index fund new models are compared with, if the fund list has it."""
    instrument = default_benchmark(session)
    return _ref(instrument) if instrument else None


@router.post("", status_code=201, operation_id="createModel")
def create(session: SessionDep, payload: ModelIn) -> ModelOut:
    """Weights must add up to exactly 100. Every fund and the benchmark become tracked."""
    return _out(session, _save(session, create_model, _input(payload)))


@router.get("/{model_id}", operation_id="getModel")
def get(session: SessionDep, model_id: int) -> ModelOut:
    return _out(session, _get(session, model_id))


@router.put("/{model_id}", operation_id="updateModel")
def update(session: SessionDep, model_id: int, payload: ModelIn) -> ModelOut:
    model = _get(session, model_id)
    return _out(session, _save(session, update_model, model, _input(payload)))


@router.post("/{model_id}/duplicate", status_code=201, operation_id="duplicateModel")
def duplicate(session: SessionDep, model_id: int) -> ModelOut:
    """A copy named "<name> copy": same funds, weights, benchmark and rebalance; no backtests."""
    return _out(session, duplicate_model(session, _get(session, model_id)))


@router.delete("/{model_id}", status_code=204, operation_id="deleteModel")
def delete(session: SessionDep, model_id: int) -> Response:
    """Delete a model and its saved backtests. Its funds' NAVs stay."""
    delete_model(session, _get(session, model_id))
    return Response(status_code=204)
