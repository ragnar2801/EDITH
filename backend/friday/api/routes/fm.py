"""Purchases and sales copied from the FM app: the receiver's details and the last import."""

import json
from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from friday.api.deps import SessionDep
from friday.core.fm.models import FmImport
from friday.core.fm.receiver import LATEST, lan_addresses
from friday.core.fm.service import import_file, last_import
from friday.core.fm.snapshot import FmSnapshotError
from friday.core.schema_types import UtcDatetime

router = APIRouter(tags=["fm"])


class FmImportOut(BaseModel):
    status: Literal["ok", "failed"]
    imported_at: UtcDatetime
    copied_at: UtcDatetime | None
    """When the copy reached Friday."""
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
    """This PC's addresses: type one into FM's Sync to PC on the phone."""
    token: str


class FmStatusOut(BaseModel):
    receiver: FmReceiverOut | None
    """Blank: the receiver is off."""
    has_copy: bool
    """A copy has been pushed, so it can be imported again."""
    last_import: FmImportOut | None


def _import(row: FmImport) -> FmImportOut:
    return FmImportOut(
        status=row.status,
        imported_at=row.imported_at,
        copied_at=row.copied_at,
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
    """Where the phone pushes to, and what the last import brought in."""
    receiver = request.app.state.fm_receiver
    row = last_import(session)
    return FmStatusOut(
        receiver=FmReceiverOut(port=receiver.port, addresses=lan_addresses(), token=receiver.token)
        if receiver
        else None,
        has_copy=(request.app.state.settings.fm_dir / LATEST).is_file(),
        last_import=_import(row) if row else None,
    )


@router.post("/fm/import", operation_id="importFm")
def import_again(request: Request) -> FmImportOut:
    """Import the latest pushed copy again, e.g. after downloading the fund list."""
    settings = request.app.state.settings
    path = settings.fm_dir / LATEST
    if not path.is_file():
        raise HTTPException(404, "Nothing has been pushed from FM yet.")
    try:
        row = import_file(
            request.app.state.session_factory, path, skip_accounts=settings.fm_skipped
        )
    except FmSnapshotError as error:
        raise HTTPException(422, f"Friday couldn't read the copy: {error}.") from None
    return _import(row)
