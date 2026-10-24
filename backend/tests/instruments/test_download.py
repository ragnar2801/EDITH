"""Downloading the lists (D-039), with a fake network."""

from pathlib import Path

import httpx2
import pytest

from friday.core.instruments.download import FetchError, FolderFetcher, HttpFetcher


def fetcher(tmp_path: Path, handler, **options) -> HttpFetcher:
    client = httpx2.Client(transport=httpx2.MockTransport(handler))
    return HttpFetcher(tmp_path / "sources", client=client, backoff_seconds=0, **options)


def test_each_source_gets_its_own_headers_and_a_saved_copy(tmp_path: Path) -> None:
    seen: dict[str, str] = {}

    def handler(request: httpx2.Request) -> httpx2.Response:
        seen[request.url.host] = request.headers["user-agent"]
        return httpx2.Response(200, content=b"\xef\xbb\xbfSYMBOL,NAME\n")

    downloads = fetcher(tmp_path, handler)

    assert downloads.get("EQUITY_L.csv") == "SYMBOL,NAME\n"  # byte-order mark dropped
    downloads.get("nasdaqlisted.txt")
    assert seen["nsearchives.nseindia.com"].startswith("Mozilla/5.0")  # NSE wants a browser
    assert seen["www.nasdaqtrader.com"].startswith("Friday/")  # Nasdaq refuses one
    assert (tmp_path / "sources" / "EQUITY_L.csv").read_bytes().startswith(b"\xef\xbb\xbf")


def test_server_errors_are_retried(tmp_path: Path) -> None:
    calls = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        calls.append(request)
        if len(calls) < 3:
            return httpx2.Response(503)
        return httpx2.Response(200, text="ok")

    assert fetcher(tmp_path, handler).get("NAVAll.txt") == "ok"
    assert len(calls) == 3


def test_network_errors_give_up_after_the_last_attempt(tmp_path: Path) -> None:
    def handler(request: httpx2.Request) -> httpx2.Response:
        raise httpx2.ConnectError("connection reset", request=request)

    with pytest.raises(FetchError, match="after 3 attempts"):
        fetcher(tmp_path, handler).get("NAVAll.txt")


def test_not_found_is_not_retried(tmp_path: Path) -> None:
    calls = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        calls.append(request)
        return httpx2.Response(404)

    with pytest.raises(FetchError, match="HTTP 404"):
        fetcher(tmp_path, handler).get("NAVAll.txt")
    assert len(calls) == 1


def test_sec_needs_a_contact_user_agent(tmp_path: Path) -> None:
    agents = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        agents.append(request.headers["user-agent"])
        return httpx2.Response(200, text="{}")

    with pytest.raises(FetchError, match="FRIDAY_SEC_USER_AGENT"):
        fetcher(tmp_path, handler).get("company_tickers_exchange.json")
    assert agents == []

    fetcher(tmp_path, handler, sec_user_agent="Me me@example.com").get(
        "company_tickers_exchange.json"
    )
    assert agents == ["Me me@example.com"]


def test_folder_fetcher(tmp_path: Path) -> None:
    (tmp_path / "NAVAll.txt").write_bytes("Scheme Code;Name\n".encode("cp1252"))

    assert FolderFetcher(tmp_path).get("NAVAll.txt") == "Scheme Code;Name\n"
    with pytest.raises(FetchError, match="not found"):
        FolderFetcher(tmp_path).get("EQUITY_L.csv")
