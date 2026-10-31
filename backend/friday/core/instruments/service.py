"""Reading instruments and setting my own classification."""

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from friday.core.instruments.classify import EXPOSURES, Classification
from friday.core.instruments.models import (
    ASSETS,
    ClassificationOverride,
    Instrument,
    InstrumentImport,
)

HUNDRED = Decimal(100)


class InvalidClassification(ValueError):
    pass


def rule_classification(instrument: Instrument) -> Classification:
    return Classification(instrument.allocation(), instrument.exposure)


def effective_classification(instrument: Instrument) -> Classification:
    """My override if I set one, otherwise what the rules say."""
    source = instrument.override or instrument
    return Classification(source.allocation(), source.exposure)


def set_override(
    session: Session,
    instrument: Instrument,
    allocation: dict[str, Decimal],
    exposure: str,
    note: str | None = None,
) -> ClassificationOverride:
    unknown = set(allocation) - set(ASSETS)
    if unknown:
        raise InvalidClassification(f"unknown asset classes: {', '.join(sorted(unknown))}")
    if any(pct < 0 or pct > HUNDRED for pct in allocation.values()):
        raise InvalidClassification("each share must be between 0 and 100")
    total = sum(allocation.values(), Decimal(0))
    if total != HUNDRED:
        raise InvalidClassification(f"shares must add up to 100, not {total}")
    if exposure not in EXPOSURES:
        raise InvalidClassification(f"exposure must be one of {', '.join(EXPOSURES)}")

    override = instrument.override or ClassificationOverride(instrument_id=instrument.id)
    override.set_allocation({asset: pct for asset, pct in allocation.items() if pct})
    override.exposure = exposure
    override.note = note or None
    override.updated_at = datetime.now(UTC)
    instrument.override = override
    session.flush()
    return override


def clear_override(session: Session, instrument: Instrument) -> None:
    instrument.override = None
    session.flush()


@dataclass(frozen=True)
class SourceStatus:
    source: str
    last_run: InstrumentImport | None
    last_success: InstrumentImport | None
    active_instruments: int


def source_statuses(session: Session) -> list[SourceStatus]:
    """Latest refresh per source, for the "lists last refreshed" line in the UI."""
    owners = {"nse": "nse", "amfi": "amfi", "us": "nasdaqtrader"}
    counts = dict(
        session.execute(
            select(Instrument.source, func.count())
            .where(Instrument.is_active)
            .group_by(Instrument.source)
        ).all()
    )

    def latest(source: str, *, ok_only: bool) -> InstrumentImport | None:
        statement = select(InstrumentImport).where(InstrumentImport.source == source)
        if ok_only:
            statement = statement.where(InstrumentImport.status == "ok")
        return session.scalars(statement.order_by(InstrumentImport.id.desc()).limit(1)).first()

    return [
        SourceStatus(
            source=source,
            last_run=latest(source, ok_only=False),
            last_success=latest(source, ok_only=True),
            active_instruments=counts.get(owner, 0),
        )
        for source, owner in owners.items()
    ]
