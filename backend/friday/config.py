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

    # Bind to this laptop only: the portfolio must not be reachable from the Wi-Fi.
    host: str = "127.0.0.1"
    port: int = 8000

    data_dir: Path = REPO_ROOT / "data"
    log_dir: Path = REPO_ROOT / "logs"
    frontend_dist: Path = REPO_ROOT / "frontend" / "dist"

    # SEC asks for a name and contact email in the User-Agent. Without it, CIKs are skipped.
    sec_user_agent: str | None = None

    # The FM app's phone pushes a copy of its database here. Off unless turned on: it is the
    # one listener on the Wi-Fi, on its own port, and takes only that copy.
    fm_push: bool = False
    fm_push_host: str = "0.0.0.0"  # noqa: S104 (the phone is on the Wi-Fi)
    fm_push_port: int = 8090
    fm_push_token: str | None = None
    """Blank: one is made and kept in ``data/fm/token.txt``."""
    fm_forward_dir: Path | None = None
    """FM desktop's documents folder: each copy is also left there for it to pick up."""
    fm_skip_accounts: str = ""
    """FM account names, comma-separated, whose purchases aren't imported."""

    @cached_property
    def sources_dir(self) -> Path:
        """Raw copies of the downloaded instrument lists."""
        return self.data_dir / "sources"

    @cached_property
    def fm_dir(self) -> Path:
        """The latest copy pushed from FM, and the receiver's token."""
        return self.data_dir / "fm"

    @cached_property
    def fm_skipped(self) -> frozenset[str]:
        return frozenset(name.strip() for name in self.fm_skip_accounts.split(",") if name.strip())

    @cached_property
    def db_path(self) -> Path:
        return self.data_dir / "friday.db"

    @cached_property
    def database_url(self) -> str:
        return f"sqlite:///{self.db_path.as_posix()}"
