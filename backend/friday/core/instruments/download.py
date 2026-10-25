"""Fetch the instrument list files (D-039): from the web, or from a folder of saved copies."""

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import httpx2

from friday import __version__
from friday.core.instruments.sources import amfi, nasdaq, nse, sec

# NSE's servers drop requests that don't look like a browser.
_BROWSER = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/130.0 Safari/537.36"
    ),
    "Accept": "text/csv,text/plain,*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nseindia.com/",
}
# Nasdaq Trader does the opposite: a browser User-Agent gets a bot-check page.
_PLAIN = {"User-Agent": f"Friday/{__version__} (personal portfolio app)"}

_NSE = "https://nsearchives.nseindia.com/content/equities/"


@dataclass(frozen=True)
class RemoteFile:
    url: str
    headers: dict[str, str]


FILES: dict[str, RemoteFile] = {
    nse.EQUITY_LIST: RemoteFile(_NSE + nse.EQUITY_LIST, _BROWSER),
    nse.ETF_LIST: RemoteFile(_NSE + nse.ETF_LIST, _BROWSER),
    nse.SYMBOL_CHANGES: RemoteFile(_NSE + nse.SYMBOL_CHANGES, _BROWSER),
    nse.NAME_CHANGES: RemoteFile(_NSE + nse.NAME_CHANGES, _BROWSER),
    amfi.NAV_ALL: RemoteFile("https://portal.amfiindia.com/spages/NAVAll.txt", _PLAIN),
    nasdaq.NASDAQ_LISTED: RemoteFile(
        "https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt", _PLAIN
    ),
    nasdaq.OTHER_LISTED: RemoteFile(
        "https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt", _PLAIN
    ),
    sec.COMPANY_TICKERS: RemoteFile(
        "https://www.sec.gov/files/company_tickers_exchange.json", {}
    ),  # User-Agent comes from FRIDAY_SEC_USER_AGENT
}


class FetchError(RuntimeError):
    """A file couldn't be downloaded or found."""


class Fetcher(Protocol):
    def get(self, file: str) -> str:
        """Return the text of one of the files in :data:`FILES`."""
        ...


def get_with_retries(
    client: httpx2.Client,
    url: str,
    headers: dict[str, str],
    *,
    attempts: int,
    backoff_seconds: float,
) -> httpx2.Response:
    """GET ``url``, retrying network errors and 5xx answers with exponential backoff.
    Anything but a 200 in the end is a :class:`FetchError`."""
    for attempt in range(1, attempts + 1):
        try:
            response = client.get(url, headers=headers)
            if response.status_code < 500:
                break
            error = f"HTTP {response.status_code}"
        except httpx2.HTTPError as exc:
            error = f"{type(exc).__name__}: {exc}"
        if attempt == attempts:
            raise FetchError(f"{url}: {error} (after {attempt} attempts)")
        time.sleep(backoff_seconds * 2 ** (attempt - 1))

    if response.status_code != 200:
        raise FetchError(f"{url}: HTTP {response.status_code}")
    return response


def decode(content: bytes) -> str:
    try:
        return content.decode("utf-8-sig")
    except UnicodeDecodeError:
        return content.decode("cp1252", errors="replace")


class FolderFetcher:
    """Reads files saved by hand (or by a previous refresh) from one folder."""

    def __init__(self, folder: Path) -> None:
        self.folder = folder

    def get(self, file: str) -> str:
        path = self.folder / file
        if not path.is_file():
            raise FetchError(f"{path} not found")
        return decode(path.read_bytes())


class HttpFetcher:
    """Downloads each file, retrying on network errors, and keeps a raw copy in ``save_dir``
    so a refresh can be repeated offline with :class:`FolderFetcher`."""

    def __init__(
        self,
        save_dir: Path,
        *,
        sec_user_agent: str | None = None,
        client: httpx2.Client | None = None,
        attempts: int = 3,
        backoff_seconds: float = 2.0,
    ) -> None:
        self.save_dir = save_dir
        self.sec_user_agent = sec_user_agent
        self.client = client or httpx2.Client(timeout=60.0, follow_redirects=True)
        self.attempts = attempts
        self.backoff_seconds = backoff_seconds

    def get(self, file: str) -> str:
        remote = FILES[file]
        headers = dict(remote.headers)
        if file == sec.COMPANY_TICKERS:
            if not self.sec_user_agent:
                raise FetchError("set FRIDAY_SEC_USER_AGENT to 'Your Name your@email' first")
            headers["User-Agent"] = self.sec_user_agent

        response = get_with_retries(
            self.client,
            remote.url,
            headers,
            attempts=self.attempts,
            backoff_seconds=self.backoff_seconds,
        )
        self.save_dir.mkdir(parents=True, exist_ok=True)
        (self.save_dir / file).write_bytes(response.content)
        return decode(response.content)
