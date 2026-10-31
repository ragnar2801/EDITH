"""The FM endpoints, read-only FM purchases, and the push receiver the phone talks to."""

import http.client
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from navs.conftest import PARAG
from sqlalchemy import select

from friday.core.db import session_scope
from friday.core.fm.receiver import FmReceiver, ensure_token
from friday.core.fm.service import FM_INCOMING, handle_push, store_copy
from friday.core.holdings.models import Lot


def push(fm, settings) -> None:
    store_copy(fm.path, settings.fm_dir / "latest.db")


def test_status_before_anything_is_pushed(client: TestClient) -> None:
    body = client.get("/api/v1/fm").json()
    assert body == {"receiver": None, "has_copy": False, "last_import": None}
    assert client.post("/api/v1/fm/import").status_code == 404


def test_import_again_reads_the_latest_copy(client, fm, settings, funds) -> None:
    fm.lot("a", "parag", "2025-04-01", 100, 20)
    push(fm, settings)

    imported = client.post("/api/v1/fm/import").json()
    assert (imported["status"], imported["lots"], imported["added"]) == ("ok", 1, 1)

    body = client.get("/api/v1/fm").json()
    assert body["has_copy"] is True
    assert body["last_import"]["lots"] == 1


@pytest.fixture
def fm_holding(client, fm, settings, funds) -> dict:
    fm.lot("a", "parag", "2025-04-01", 100, 20)
    fm.sell("s1", "a", "2026-02-14", 40, 30)
    push(fm, settings)
    client.post("/api/v1/fm/import")
    return client.get(f"/api/v1/holdings/{funds[PARAG]}").json()


def test_fm_purchases_are_read_only(client, fm_holding) -> None:
    lot = fm_holding["lots"][0]
    assert (lot["source"], lot["note"], lot["units_remaining"]) == ("fm", "grow mf", "60.00000000")

    edit = {"buy_date": "2025-04-01", "amount": "1000", "nav": "10"}
    sale = {"sale_date": "2026-03-01", "nav": "30", "lots": [{"lot_id": lot["id"], "units": "1"}]}
    for response in (
        client.put(f"/api/v1/lots/{lot['id']}", json=edit),
        client.delete(f"/api/v1/lots/{lot['id']}"),
        client.post("/api/v1/sales", json=sale),
        client.delete(f"/api/v1/sales/{lot['sales'][0]['id']}"),
    ):
        assert response.status_code == 409
        assert response.json()["detail"] == "This purchase comes from FM; change it there."


@pytest.fixture
def receiver(settings, factory, tmp_path):
    forward = tmp_path / "Documents"
    token = ensure_token(settings.fm_dir, None)
    server = FmReceiver(
        folder=settings.fm_dir,
        token=token,
        host="127.0.0.1",
        port=0,
        on_push=lambda path: handle_push(factory, path, forward_dir=forward),
    )
    server.start()
    yield server, forward
    server.stop()


def call(server: FmReceiver, method: str, path: str, body: bytes = b"", token: str | None = None):
    connection = http.client.HTTPConnection("127.0.0.1", server.port, timeout=10)
    headers = {"x-sync-token": token} if token is not None else {}
    connection.request(method, path, body=body, headers=headers)
    response = connection.getresponse()
    answer = (response.status, response.read().decode())
    connection.close()
    return answer


def test_the_phone_can_push(receiver, fm, factory, funds, settings) -> None:
    server, forward = receiver
    fm.lot("a", "parag", "2025-04-01", 100, 20)
    data = Path(fm.path).read_bytes()

    assert call(server, "GET", "/health") == (200, "ok")
    assert call(server, "POST", "/db", data, token="wrong")[0] == 401
    assert call(server, "GET", "/api/v1/fm")[0] == 404  # nothing but the push is served

    assert call(server, "POST", "/db", data, token=server.token) == (
        200,
        "Friday imported 1 purchases and 0 sales of 1 funds.",
    )
    assert (settings.fm_dir / "latest.db").read_bytes() == data
    assert (forward / FM_INCOMING).read_bytes() == data  # FM desktop picks it up on start
    with session_scope(factory) as session:
        assert session.scalars(select(Lot.source_id)).all() == ["a"]

    assert call(server, "POST", "/db", b"not a database", token=server.token) == (
        422,
        "Friday couldn't read the copy: latest.db isn't a database file",
    )
    assert (forward / FM_INCOMING).read_bytes() == data  # the bad copy isn't handed on


def test_the_token_is_kept(settings) -> None:
    token = ensure_token(settings.fm_dir, None)
    assert ensure_token(settings.fm_dir, None) == token
    assert ensure_token(settings.fm_dir, " mine ") == "mine"
