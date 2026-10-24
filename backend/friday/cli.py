"""``friday`` command: serve, migrate, export the OpenAPI schema, refresh and search instruments."""

import argparse
import json
from pathlib import Path

import uvicorn

from friday.config import BACKEND_DIR, Settings
from friday.core.db import upgrade_database


def _serve(args: argparse.Namespace) -> None:
    settings = Settings()
    uvicorn.run(
        "friday.main:app",
        host=settings.host,
        port=args.port or settings.port,
        reload=args.reload,
        reload_dirs=[str(BACKEND_DIR / "friday")] if args.reload else None,
    )


def _migrate(_args: argparse.Namespace) -> None:
    upgrade_database(Settings())
    print("Database is up to date.")


def _openapi(args: argparse.Namespace) -> None:
    from friday.api.app import create_app

    schema = create_app(migrate=False).openapi()
    text = json.dumps(schema, indent=2, sort_keys=True) + "\n"
    Path(args.out).write_text(text, encoding="utf-8", newline="\n")
    print(f"Wrote {args.out}")


def _refresh_instruments(args: argparse.Namespace) -> None:
    from friday.core.db import make_engine, make_session_factory
    from friday.core.instruments.download import FolderFetcher, HttpFetcher
    from friday.core.instruments.refresh import refresh_instruments

    settings = Settings()
    upgrade_database(settings)
    engine = make_engine(settings)
    if args.from_dir:
        fetcher = FolderFetcher(Path(args.from_dir))
    else:
        fetcher = HttpFetcher(settings.sources_dir, sec_user_agent=settings.sec_user_agent)
    try:
        results = refresh_instruments(make_session_factory(engine), fetcher, args.source)
    finally:
        engine.dispose()

    for result in results:
        if result.status == "ok":
            print(
                f"{result.source:5} ok      {result.rows:6} rows · {result.added} added · "
                f"{result.updated} updated · {result.deactivated} deactivated · "
                f"{result.reactivated} reactivated · {result.aliases_added} aliases"
            )
        else:
            print(f"{result.source:5} FAILED  {result.message}")
        for warning in result.warnings:
            print(f"      note: {warning}")
    if any(result.status != "ok" for result in results):
        raise SystemExit(1)


def _search_instruments(args: argparse.Namespace) -> None:
    from friday.core.db import make_engine, make_session_factory, session_scope
    from friday.core.instruments.search import search_instruments
    from friday.core.instruments.service import effective_classification

    settings = Settings()
    engine = make_engine(settings)
    with session_scope(make_session_factory(engine)) as session:
        hits = search_instruments(session, " ".join(args.query), limit=args.limit)
        for hit in hits:
            i = hit.instrument
            where = f"{i.exchange}:{i.symbol}" if i.symbol else f"AMFI {i.amfi_code}"
            label = effective_classification(i).asset_class
            more = f" (+{len(hit.variants)} variants)" if hit.variants else ""
            print(f"{i.id:6}  {where:22} {i.kind:11} {i.currency} {label:12} {i.name}{more}")
    engine.dispose()
    if not hits:
        print("No matches.")


def main() -> None:
    parser = argparse.ArgumentParser(prog="friday")
    commands = parser.add_subparsers(required=True)

    serve = commands.add_parser("serve", help="run the Friday server")
    serve.add_argument("--reload", action="store_true", help="restart on code changes (dev)")
    serve.add_argument("--port", type=int, default=None)
    serve.set_defaults(func=_serve)

    migrate = commands.add_parser("migrate", help="upgrade the database to the latest schema")
    migrate.set_defaults(func=_migrate)

    openapi = commands.add_parser("openapi", help="write the OpenAPI schema to a file")
    openapi.add_argument("--out", required=True)
    openapi.set_defaults(func=_openapi)

    instruments = commands.add_parser("instruments", help="instrument lists and search")
    instrument_commands = instruments.add_subparsers(required=True)

    refresh = instrument_commands.add_parser(
        "refresh", help="download the NSE, AMFI and US lists and update instruments"
    )
    refresh.add_argument(
        "--source",
        nargs="+",
        choices=["nse", "amfi", "us"],
        default=["nse", "amfi", "us"],
        help="refresh only these sources",
    )
    refresh.add_argument(
        "--from-dir", help="import files saved in this folder instead of downloading"
    )
    refresh.set_defaults(func=_refresh_instruments)

    search = instrument_commands.add_parser("search", help="search instruments by name or code")
    search.add_argument("query", nargs="+")
    search.add_argument("--limit", type=int, default=10)
    search.set_defaults(func=_search_instruments)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
