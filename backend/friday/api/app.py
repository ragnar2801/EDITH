"""FastAPI application factory."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from friday import __version__
from friday.api.errors import PROBLEM_RESPONSES, install_error_handlers
from friday.api.frontend import mount_frontend
from friday.api.routes import backtests, buckets, cash, holdings, instruments, navs, system
from friday.config import Settings
from friday.core.db import make_engine, make_session_factory, upgrade_database
from friday.core.navs.download import HttpNavFetcher

API_PREFIX = "/api/v1"


def create_app(settings: Settings | None = None, *, migrate: bool = True) -> FastAPI:
    settings = settings or Settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        if migrate:
            upgrade_database(settings)
        yield
        app.state.engine.dispose()
        close = getattr(app.state.nav_fetcher, "close", None)
        if close:
            close()

    app = FastAPI(title="Friday", version=__version__, lifespan=lifespan)
    app.state.settings = settings
    app.state.engine = make_engine(settings)
    app.state.session_factory = make_session_factory(app.state.engine)
    app.state.nav_fetcher = HttpNavFetcher()  # tests replace it with a fake

    install_error_handlers(app)
    app.include_router(system.router, prefix=API_PREFIX, responses=PROBLEM_RESPONSES)
    app.include_router(instruments.router, prefix=API_PREFIX, responses=PROBLEM_RESPONSES)
    app.include_router(navs.router, prefix=API_PREFIX, responses=PROBLEM_RESPONSES)
    app.include_router(buckets.router, prefix=API_PREFIX, responses=PROBLEM_RESPONSES)
    app.include_router(backtests.router, prefix=API_PREFIX, responses=PROBLEM_RESPONSES)
    app.include_router(holdings.router, prefix=API_PREFIX, responses=PROBLEM_RESPONSES)
    app.include_router(cash.router, prefix=API_PREFIX, responses=PROBLEM_RESPONSES)
    mount_frontend(app, settings.frontend_dist)  # must be last: it catches every other path
    return app
