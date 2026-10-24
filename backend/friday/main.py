"""ASGI entry point used by ``friday serve``."""

from friday.api.app import create_app

app = create_app()
