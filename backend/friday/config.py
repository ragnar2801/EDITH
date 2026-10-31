"""Runtime settings, from environment variables (prefix ``FRIDAY_``) or the repo-root ``.env``."""

import os
from functools import cached_property
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_DIR.parent


def _home() -> Path:
    """Where my real data lives: outside the repo, so nothing working on the code finds it."""
    local = os.environ.get("LOCALAPPDATA")
    return Path(local) / "Friday" if local else Path.home() / ".local" / "share" / "friday"


HOME = _home()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="FRIDAY_",
        env_file=REPO_ROOT / ".env",
        extra="ignore",
    )

    # Bind to this laptop only: the portfolio must not be reachable from the Wi-Fi.
    host: str = "127.0.0.1"
    port: int = 8000

    data_dir: Path = HOME / "data"
    log_dir: Path = HOME / "logs"
    frontend_dist: Path = REPO_ROOT / "frontend" / "dist"

    # SEC asks for a name and contact email in the User-Agent. Without it, CIKs are skipped.
    sec_user_agent: str | None = None

    # FM on the phone sends its lots here ("Sync to Friday"). The one listener on the Wi-Fi:
    # its own port, a token (made in fm/token.txt in the data folder), and nothing served
    # but the lots.
    fm_push: bool = True
    fm_push_port: int = 8090

    @cached_property
    def sources_dir(self) -> Path:
        """Raw copies of the downloaded instrument lists."""
        return self.data_dir / "sources"

    @cached_property
    def fm_dir(self) -> Path:
        """The FM receiver's token."""
        return self.data_dir / "fm"

    @cached_property
    def db_path(self) -> Path:
        return self.data_dir / "friday.db"

    @cached_property
    def database_url(self) -> str:
        return f"sqlite:///{self.db_path.as_posix()}"
