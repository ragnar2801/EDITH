"""``friday`` command: serve, migrate, export the OpenAPI schema."""

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

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
