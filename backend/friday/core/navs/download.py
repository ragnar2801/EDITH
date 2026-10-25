"""Fetch NAVs (D-044): one fund's history from mfapi.in, or AMFI's latest-NAV file."""

from typing import Protocol

import httpx2

from friday import __version__
from friday.core.instruments.download import FILES, decode, get_with_retries
from friday.core.instruments.sources import amfi

MFAPI_URL = "https://api.mfapi.in/mf/{code}"
_HEADERS = {"User-Agent": f"Friday/{__version__} (personal portfolio app)"}


class NavFetcher(Protocol):
    def history(self, amfi_code: str) -> str:
        """mfapi.in's JSON for one scheme: its whole NAV history."""
        ...

    def latest(self) -> str:
        """AMFI's ``NAVAll.txt``: the latest NAV of every scheme."""
        ...


class HttpNavFetcher:
    def __init__(
        self,
        *,
        client: httpx2.Client | None = None,
        attempts: int = 3,
        backoff_seconds: float = 2.0,
    ) -> None:
        self.client = client or httpx2.Client(timeout=60.0, follow_redirects=True)
        self.attempts = attempts
        self.backoff_seconds = backoff_seconds

    def _get(self, url: str, headers: dict[str, str]) -> str:
        response = get_with_retries(
            self.client,
            url,
            headers,
            attempts=self.attempts,
            backoff_seconds=self.backoff_seconds,
        )
        return decode(response.content)

    def history(self, amfi_code: str) -> str:
        return self._get(MFAPI_URL.format(code=amfi_code), _HEADERS)

    def latest(self) -> str:
        remote = FILES[amfi.NAV_ALL]
        return self._get(remote.url, remote.headers)

    def close(self) -> None:
        self.client.close()
