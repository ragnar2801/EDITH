"""Creating and changing models.

Weights are exact percentages that must add up to exactly 100: a split that only looks
like 100% is refused rather than quietly normalised. Only AMFI schemes can be in a model
or be its benchmark. Everything in a model is tracked for NAVs.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from friday.core.instruments.models import Instrument
from friday.core.models.models import REBALANCE, Model, ModelFund

HUNDRED = Decimal(100)

DEFAULT_BENCHMARK = "120716"
"""UTI Nifty 50 Index Fund – Direct Plan – Growth: the Nifty 50, dividends included."""


class InvalidModel(ValueError):
    pass


class DuplicateModel(ValueError):
    pass


@dataclass(frozen=True)
class ModelInput:
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
        raise InvalidModel(f"{role}: no instrument with id {instrument_id}")
    if not instrument.amfi_code:
        raise InvalidModel(f"{role}: {instrument.name} is not a mutual fund scheme")
    return instrument


def check_split(session: Session, funds: list[tuple[int, Decimal]]) -> list[Instrument]:
    """The funds of a split, if it's one a model could have (also a backtest's)."""
    if not funds:
        raise InvalidModel("add at least one fund")
    ids = [instrument_id for instrument_id, _ in funds]
    if len(set(ids)) != len(ids):
        raise InvalidModel("a fund is listed twice")
    instruments = []
    for instrument_id, weight in funds:
        fund = _fund(session, instrument_id, "fund")
        if weight <= 0 or weight > HUNDRED:
            raise InvalidModel(f"{fund.name}: weight must be more than 0 and at most 100")
        instruments.append(fund)
    total = sum((weight for _, weight in funds), Decimal(0))
    if total != HUNDRED:
        raise InvalidModel(f"weights must add up to 100, not {total.normalize():f}")
    return instruments


def _validate(session: Session, data: ModelInput, model_id: int | None) -> str:
    name = " ".join(data.name.split())
    if not name:
        raise InvalidModel("give the model a name")
    if data.rebalance not in REBALANCE:
        raise InvalidModel(f"rebalance must be one of {', '.join(REBALANCE)}")
    check_split(session, data.funds)
    if data.benchmark_id is not None:
        _fund(session, data.benchmark_id, "benchmark")

    clash = session.scalars(select(Model).where(Model.name == name)).first()
    if clash is not None and clash.id != model_id:
        raise DuplicateModel(f"there is already a model called {name}")
    return name


def _apply(model: Model, data: ModelInput, name: str, now: datetime) -> None:
    model.name = name
    model.description = (data.description or "").strip() or None
    model.rebalance = data.rebalance
    model.benchmark_id = data.benchmark_id
    model.updated_at = now
    weights = dict(data.funds)
    positions = {instrument_id: i for i, (instrument_id, _) in enumerate(data.funds)}
    kept = []
    for member in model.funds:
        if member.instrument_id in weights:
            member.weight_pct = weights.pop(member.instrument_id)
            member.position = positions[member.instrument_id]
            kept.append(member)
    model.funds = kept + [
        ModelFund(instrument_id=instrument_id, weight_pct=weight, position=positions[instrument_id])
        for instrument_id, weight in weights.items()
    ]


def create_model(session: Session, data: ModelInput) -> Model:
    name = _validate(session, data, None)
    now = datetime.now(UTC)
    model = Model(created_at=now)
    _apply(model, data, name, now)
    session.add(model)
    session.flush()
    return model


def update_model(session: Session, model: Model, data: ModelInput) -> Model:
    name = _validate(session, data, model.id)
    _apply(model, data, name, datetime.now(UTC))
    session.flush()
    session.refresh(model)
    return model


def duplicate_model(session: Session, model: Model) -> Model:
    """A copy named ``<name> copy`` (``copy 2``, … if taken), without its backtests."""
    taken = set(session.scalars(select(Model.name)))
    name = f"{model.name} copy"
    number = 2
    while name in taken:
        name = f"{model.name} copy {number}"
        number += 1
    data = ModelInput(
        name=name,
        funds=[(member.instrument_id, member.weight_pct) for member in model.funds],
        rebalance=model.rebalance,
        benchmark_id=model.benchmark_id,
        description=model.description,
    )
    return create_model(session, data)


def delete_model(session: Session, model: Model) -> None:
    session.delete(model)
    session.flush()


def list_models(session: Session) -> list[Model]:
    return list(session.scalars(select(Model).order_by(Model.name)))


def model_reasons(session: Session) -> dict[int, list[str]]:
    """Every fund a model uses, with why: ``model <name>`` or ``benchmark of <name>``."""
    reasons: dict[int, list[str]] = {}
    for model in list_models(session):
        for member in model.funds:
            reasons.setdefault(member.instrument_id, []).append(f"model {model.name}")
        if model.benchmark_id is not None:
            reasons.setdefault(model.benchmark_id, []).append(f"benchmark of {model.name}")
    return reasons
