"""Serve the built React app in daily mode. Unknown non-API paths get ``index.html``."""

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, Response

_NOT_BUILT = """<!doctype html><title>Friday</title>
<p>The frontend isn't built yet. Run <code>just build</code>, then reload.</p>
<p>API health: <a href="/api/v1/health">/api/v1/health</a></p>"""


def mount_frontend(app: FastAPI, dist: Path) -> None:
    dist = dist.resolve()

    @app.get("/{path:path}", include_in_schema=False, response_model=None)
    def frontend(path: str) -> Response:
        if path == "api" or path.startswith("api/"):
            raise HTTPException(status_code=404)
        index = dist / "index.html"
        if not index.is_file():
            return HTMLResponse(_NOT_BUILT, status_code=503)
        candidate = (dist / path).resolve()
        if path and candidate.is_file() and candidate.is_relative_to(dist):
            return FileResponse(candidate)
        return FileResponse(index)
