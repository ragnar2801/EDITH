"""Run the backend and frontend dev servers together (``just dev``). Ctrl+C stops both."""

import os
import shutil
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _tool(name: str) -> str:
    # npm.ps1 is blocked by Windows' default script policy; npm.cmd is not.
    if os.name == "nt" and name == "npm":
        name = "npm.cmd"
    path = shutil.which(name)
    if path is None:
        raise SystemExit(f"{name} not found on PATH. See README.md for setup.")
    return path


def main() -> None:
    commands = [
        [_tool("uv"), "run", "--project", "backend", "friday", "serve", "--reload"],
        [_tool("npm"), "--prefix", "frontend", "run", "dev"],
    ]
    processes = [subprocess.Popen(command, cwd=ROOT) for command in commands]
    print("Friday dev mode: open http://localhost:5173 (API on :8000). Ctrl+C to stop.")
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
