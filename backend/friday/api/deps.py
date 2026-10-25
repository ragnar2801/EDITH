"""Shared FastAPI dependencies."""

from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from friday.core.db import session_scope


def get_session(request: Request) -> Iterator[Session]:
    with session_scope(request.app.state.session_factory) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]
