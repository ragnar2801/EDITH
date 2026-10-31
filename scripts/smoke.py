"""Smoke test (``just smoke``): start the real server on a spare port with a throwaway
database, check the API and the built UI answer, then stop it."""

import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _get(url: str) -> tuple[int, str]:
    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            return response.status, response.read().decode()
    except urllib.error.HTTPError as error:
        return error.code, error.read().decode()


def _wait_for_health(base: str, server: subprocess.Popen[bytes]) -> dict[str, object]:
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        if server.poll() is not None:
            raise SystemExit(f"server exited early with code {server.returncode}")
        try:
            status, body = _get(f"{base}/api/v1/health")
            if status == 200:
                return json.loads(body)
        except urllib.error.URLError, ConnectionError:
            pass
        time.sleep(0.5)
    raise SystemExit("server did not answer /api/v1/health within 60 seconds")


def main() -> None:
    port = _free_port()
    base = f"http://127.0.0.1:{port}"
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        env = {
            **os.environ,
            "FRIDAY_DATA_DIR": str(Path(tmp) / "data"),
            "FRIDAY_LOG_DIR": str(Path(tmp) / "logs"),
            "FRIDAY_FM_PUSH": "false",  # leave the FM port to the real Friday
        }
        server = subprocess.Popen(
            [sys.executable, "-m", "friday.cli", "serve", "--port", str(port)], cwd=ROOT, env=env
        )
        try:
            health = _wait_for_health(base, server)
            assert health["status"] == "ok" and health["database"] == "ok", health
            print(f"ok  /api/v1/health  {health}")

            status, body = _get(f"{base}/api/v1/instruments/search?q=infosys")
            assert status == 200 and body.startswith("["), (status, body)
            print("ok  /api/v1/instruments/search  answers (empty until `just instruments`)")

            for path in ["/", "/holdings", "/instruments"]:
                status, body = _get(f"{base}{path}")
                if status == 503:
                    raise SystemExit("UI is not built. Run `just build` first.")
                assert status == 200 and '<div id="root">' in body, (path, status)
                print(f"ok  {path}  serves the UI")
        finally:
            server.terminate()
            server.wait(timeout=15)
    print("Smoke test passed.")


if __name__ == "__main__":
    main()
