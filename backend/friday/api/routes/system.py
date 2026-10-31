"""Health check and the money/time round-trip used to prove the conventions."""

from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, Request
from pydantic import BaseModel
from sqlalchemy import text

from friday import __version__
from friday.core.schema_types import Money, UtcDatetime

router = APIRouter(tags=["system"])


class Health(BaseModel):
    status: Literal["ok"]
    version: str
    database: Literal["ok", "error"]
    server_time: UtcDatetime


class Echo(BaseModel):
    money: Money
    at: UtcDatetime


@router.get("/health", operation_id="getHealth")
def get_health(request: Request) -> Health:
    try:
        with request.app.state.engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        database: Literal["ok", "error"] = "ok"
    except Exception:
        database = "error"
    return Health(
        status="ok", version=__version__, database=database, server_time=datetime.now(UTC)
    )


@router.post("/diagnostics/echo", operation_id="echo")
def echo(payload: Echo) -> Echo:
    """Return the payload unchanged, so tests can prove amounts and timestamps survive."""
    return payload
