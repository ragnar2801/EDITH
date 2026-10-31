"""``friday`` command: serve, migrate, export the OpenAPI schema, refresh and search instruments,
track funds and sync their NAVs, import from FM."""

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


def _funds_by_code(session, codes: list[str]) -> list:
    from sqlalchemy import select

    from friday.core.instruments.models import Instrument

    found = {
        instrument.amfi_code: instrument
        for instrument in session.scalars(select(Instrument).where(Instrument.amfi_code.in_(codes)))
    }
    unknown = [code for code in codes if code not in found]
    if unknown:
        raise SystemExit(
            f"Unknown AMFI scheme codes: {', '.join(unknown)}. Run `just instruments` first?"
        )
    return [found[code] for code in codes]


def _track_funds(args: argparse.Namespace) -> None:
    from friday.core.db import make_engine, make_session_factory, session_scope
    from friday.core.navs.service import NotAFund, track

    settings = Settings()
    upgrade_database(settings)
    engine = make_engine(settings)
    with session_scope(make_session_factory(engine)) as session:
        for instrument in _funds_by_code(session, args.codes):
            try:
                track(session, instrument)
            except NotAFund as error:
                raise SystemExit(str(error)) from None
            print(f"tracking  AMFI {instrument.amfi_code}  {instrument.name}")
    engine.dispose()
    print("Run `just navs` to download their NAV history.")


def _sync_navs(args: argparse.Namespace) -> None:
    from friday.core.db import make_engine, make_session_factory, session_scope
    from friday.core.navs.download import HttpNavFetcher
    from friday.core.navs.service import NotTracked, sync_navs

    settings = Settings()
    upgrade_database(settings)
    engine = make_engine(settings)
    factory = make_session_factory(engine)
    ids = None
    if args.fund:
        with session_scope(factory) as session:
            ids = [instrument.id for instrument in _funds_by_code(session, args.fund)]
    fetcher = HttpNavFetcher()
    try:
        result = sync_navs(factory, fetcher, ids)
    except NotTracked as error:
        raise SystemExit(f"Track these funds first: {error}") from None
    finally:
        fetcher.close()
        engine.dispose()

    for fund in result.results:
        last = fund.last_date.isoformat() if fund.last_date else "-"
        print(f"{fund.status:8} {fund.added:5} added  last {last}  {fund.name}")
        if fund.message:
            print(f"         note: {fund.message}")
    if not result.results:
        print("No funds tracked yet. Track some with `friday navs track <AMFI code>`.")
    print(f"Sync {result.status}: {result.added} NAVs added.")
    if result.status != "ok":
        raise SystemExit(1)


def _import_fm(args: argparse.Namespace) -> None:
    from friday.core.db import make_engine, make_session_factory
    from friday.core.fm.receiver import LATEST
    from friday.core.fm.service import apply_snapshot, import_file
    from friday.core.fm.snapshot import FmSnapshotError, read_snapshot

    settings = Settings()
    path = args.path or settings.fm_dir / LATEST
    upgrade_database(settings)
    engine = make_engine(settings)
    factory = make_session_factory(engine)
    try:
        if args.dry_run:
            session = factory()
            try:
                result = apply_snapshot(
                    session, read_snapshot(path, skip_accounts=settings.fm_skipped)
                )
            finally:
                session.rollback()
                session.close()
            counts = (result.funds, result.lots, result.sales, result.added, result.removed)
            warnings = result.warnings
        else:
            row = import_file(factory, path, skip_accounts=settings.fm_skipped)
            counts = (row.funds, row.lots, row.sales, row.added, row.removed)
            warnings = json.loads(row.warnings)
    except FmSnapshotError as error:
        raise SystemExit(f"Can't import {path}: {error}") from None
    finally:
        engine.dispose()

    funds, lots, sales, added, removed = counts
    verb = "Would import" if args.dry_run else "Imported"
    print(
        f"{verb} {lots} purchases and {sales} sales of {funds} funds ({added} new, {removed} gone)."
    )
    for warning in warnings:
        print(f"  note: {warning}")


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

    navs = commands.add_parser("navs", help="fund NAVs: track funds and sync their NAVs")
    nav_commands = navs.add_subparsers(required=True)

    nav_sync = nav_commands.add_parser(
        "sync", help="download missing NAVs for every tracked fund, up to today"
    )
    nav_sync.add_argument("--fund", nargs="+", metavar="AMFI_CODE", help="only these funds")
    nav_sync.set_defaults(func=_sync_navs)

    nav_track = nav_commands.add_parser("track", help="keep NAVs for these funds")
    nav_track.add_argument("codes", nargs="+", metavar="AMFI_CODE")
    nav_track.set_defaults(func=_track_funds)

    fm = commands.add_parser("fm", help="purchases and sales copied from the FM app")
    fm_commands = fm.add_subparsers(required=True)
    fm_import = fm_commands.add_parser(
        "import", help="import an FM database copy (default: the latest one pushed)"
    )
    fm_import.add_argument("path", nargs="?", type=Path)
    fm_import.add_argument("--dry-run", action="store_true", help="show what would change")
    fm_import.set_defaults(func=_import_fm)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
