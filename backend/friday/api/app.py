"""FastAPI application factory."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from friday import __version__
from friday.api.errors import PROBLEM_RESPONSES, install_error_handlers
from friday.api.frontend import mount_frontend
from friday.api.routes import (
    backtests,
    buckets,
    cash,
    fm,
    holdings,
    instruments,
    navs,
    portfolio,
    system,
)
from friday.config import Settings
from friday.core.db import make_engine, make_session_factory, upgrade_database
from friday.core.fm.receiver import FmReceiver, ensure_token
from friday.core.fm.service import handle_push
from friday.core.instruments.download import HttpFetcher
from friday.core.navs.download import HttpNavFetcher

API_PREFIX = "/api/v1"

log = logging.getLogger(__name__)


def create_app(settings: Settings | None = None, *, migrate: bool = True) -> FastAPI:
    settings = settings or Settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        if migrate:
            upgrade_database(settings)
        if settings.fm_push:
            try:
                app.state.fm_receiver = _fm_receiver(app)
                app.state.fm_receiver.start()
            except OSError as error:  # the port is taken, e.g. by a second Friday
                log.warning("FM receiver not started on port %s: %s", settings.fm_push_port, error)
        yield
        if app.state.fm_receiver:
            app.state.fm_receiver.stop()
        app.state.engine.dispose()
        for fetcher in (app.state.nav_fetcher, app.state.list_fetcher):
            close = getattr(fetcher, "close", None)
            if close:
                close()

    app = FastAPI(title="Friday", version=__version__, lifespan=lifespan)
    app.state.settings = settings
    app.state.engine = make_engine(settings)
    app.state.session_factory = make_session_factory(app.state.engine)
    app.state.nav_fetcher = HttpNavFetcher()  # tests replace it with a fake
    app.state.fm_receiver = None  # started with the app unless FRIDAY_FM_PUSH is off
    app.state.list_fetcher = HttpFetcher(  # instrument lists; tests use a folder
        settings.sources_dir, sec_user_agent=settings.sec_user_agent
    )

    install_error_handlers(app)
    app.include_router(system.router, prefix=API_PREFIX, responses=PROBLEM_RESPONSES)
    app.include_router(instruments.router, prefix=API_PREFIX, responses=PROBLEM_RESPONSES)
    app.include_router(navs.router, prefix=API_PREFIX, responses=PROBLEM_RESPONSES)
    app.include_router(buckets.router, prefix=API_PREFIX, responses=PROBLEM_RESPONSES)
    app.include_router(backtests.router, prefix=API_PREFIX, responses=PROBLEM_RESPONSES)
    app.include_router(holdings.router, prefix=API_PREFIX, responses=PROBLEM_RESPONSES)
    app.include_router(cash.router, prefix=API_PREFIX, responses=PROBLEM_RESPONSES)
    app.include_router(portfolio.router, prefix=API_PREFIX, responses=PROBLEM_RESPONSES)
    app.include_router(fm.router, prefix=API_PREFIX, responses=PROBLEM_RESPONSES)
    mount_frontend(app, settings.frontend_dist)  # must be last: it catches every other path
    return app


def _fm_receiver(app: FastAPI) -> FmReceiver:
    settings: Settings = app.state.settings
    return FmReceiver(
        token=ensure_token(settings.fm_dir),
        port=settings.fm_push_port,
        on_push=lambda body: handle_push(app.state.session_factory, body),
    )
