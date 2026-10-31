"""Purchases and sales sent from the FM app: where to send them, and the last import."""

import json
from typing import Literal

from fastapi import APIRouter, Request
from pydantic import BaseModel

from friday.api.deps import SessionDep
from friday.core.fm.models import FmImport
from friday.core.fm.receiver import lan_addresses
from friday.core.fm.service import last_import
from friday.core.schema_types import UtcDatetime

router = APIRouter(tags=["fm"])


class FmImportOut(BaseModel):
    status: Literal["ok", "failed"]
    imported_at: UtcDatetime
    sent_at: UtcDatetime | None
    """When FM built the lots it sent."""
    funds: int
    lots: int
    sales: int
    added: int
    """Purchases that weren't there at the import before."""
    removed: int
    warnings: list[str]
    message: str | None


class FmReceiverOut(BaseModel):
    port: int
    addresses: list[str]
    """This PC's addresses: type one into FM's Sync to Friday on the phone."""
    token: str


class FmStatusOut(BaseModel):
    receiver: FmReceiverOut | None
    """Blank: the receiver is off."""
    last_import: FmImportOut | None


def _import(row: FmImport) -> FmImportOut:
    return FmImportOut(
        status=row.status,
        imported_at=row.imported_at,
        sent_at=row.sent_at,
        funds=row.funds,
        lots=row.lots,
        sales=row.sales,
        added=row.added,
        removed=row.removed,
        warnings=json.loads(row.warnings),
        message=row.message,
    )


@router.get("/fm", operation_id="getFmStatus")
def status(request: Request, session: SessionDep) -> FmStatusOut:
    """Where the phone sends its lots, and what the last import brought in."""
    receiver = request.app.state.fm_receiver
    row = last_import(session)
    return FmStatusOut(
        receiver=FmReceiverOut(port=receiver.port, addresses=lan_addresses(), token=receiver.token)
        if receiver
        else None,
        last_import=_import(row) if row else None,
    )
