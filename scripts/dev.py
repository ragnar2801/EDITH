"""Run the backend and frontend dev servers together (``just dev``). Ctrl+C stops both.

Dev mode runs on the made-up database in ``dev/`` (built on first run, rebuilt with
``just demo``), never on the real one, so the app can be run and screenshotted freely. Its
API is on :8001 and it doesn't listen for FM, so the real Friday can run alongside.
"""

import argparse
import os
import shutil
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEV_DIR = ROOT / "dev"
API_PORT = "8001"


def _tool(name: str) -> str:
    # npm.ps1 is blocked by Windows' default script policy; npm.cmd is not.
    if os.name == "nt" and name == "npm":
        name = "npm.cmd"
    path = shutil.which(name)
    if path is None:
        raise SystemExit(f"{name} not found on PATH. See README.md for setup.")
    return path


def _env() -> dict[str, str]:
    return {
        **os.environ,
        "FRIDAY_DATA_DIR": str(DEV_DIR / "data"),
        "FRIDAY_LOG_DIR": str(DEV_DIR / "logs"),
        "FRIDAY_FM_PUSH": "false",
    }


def _build_demo(env: dict[str, str]) -> None:
    print("Building the demo database (downloads public fund NAVs)...")
    command = [_tool("uv"), "run", "--project", "backend", "friday", "demo"]
    if subprocess.run(command, cwd=ROOT, env=env).returncode != 0:
        shutil.rmtree(DEV_DIR, ignore_errors=True)
        raise SystemExit("Couldn't build the demo database.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rebuild", action="store_true", help="rebuild the demo database only")
    args = parser.parse_args()

    env = _env()
    if args.rebuild:
        shutil.rmtree(DEV_DIR, ignore_errors=True)
    if not (DEV_DIR / "data" / "friday.db").exists():
        _build_demo(env)
    if args.rebuild:
        return

    commands = [
        [_tool("uv"), "run", "--project", "backend", "friday", "serve", "--reload"]
        + ["--port", API_PORT],
        [_tool("npm"), "--prefix", "frontend", "run", "dev"],
    ]
    processes = [subprocess.Popen(command, cwd=ROOT, env=env) for command in commands]
    print(f"Friday dev mode (demo data): open http://localhost:5173 (API on :{API_PORT}).")
    print("Ctrl+C to stop.")
    try:
        while all(process.poll() is None for process in processes):
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    finally:
        for process in processes:
            if process.poll() is None:
                process.terminate()
        for process in processes:
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()


if __name__ == "__main__":
    main()
