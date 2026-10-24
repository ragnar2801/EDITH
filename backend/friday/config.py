"""Runtime settings, from environment variables (prefix ``FRIDAY_``) or the repo-root ``.env``."""

from functools import cached_property
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="FRIDAY_",
        env_file=REPO_ROOT / ".env",
        extra="ignore",
    )

    # Bind to this laptop only (D-036): the portfolio must not be reachable from the Wi-Fi.
    host: str = "127.0.0.1"
    port: int = 8000

    data_dir: Path = REPO_ROOT / "data"
    log_dir: Path = REPO_ROOT / "logs"
    frontend_dist: Path = REPO_ROOT / "frontend" / "dist"

    # SEC asks for a name and contact email in the User-Agent. Without it, CIKs are skipped.
    sec_user_agent: str | None = None

    @cached_property
    def sources_dir(self) -> Path:
        """Raw copies of the downloaded instrument lists (D-039)."""
        return self.data_dir / "sources"

    @cached_property
    def db_path(self) -> Path:
        return self.data_dir / "friday.db"

    @cached_property
    def database_url(self) -> str:
        return f"sqlite:///{self.db_path.as_posix()}"
