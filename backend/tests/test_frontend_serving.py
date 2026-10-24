from pathlib import Path

from fastapi.testclient import TestClient

from friday.api.app import create_app
from friday.config import Settings


def test_root_serves_index(client: TestClient) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert '<div id="root">' in response.text


def test_client_side_routes_fall_back_to_index(client: TestClient) -> None:
    response = client.get("/holdings")

    assert response.status_code == 200
    assert '<div id="root">' in response.text


def test_built_assets_are_served(client: TestClient) -> None:
    response = client.get("/assets/app.js")

    assert response.status_code == 200
    assert "friday" in response.text


def test_paths_outside_dist_are_not_served(client: TestClient, settings: Settings) -> None:
    (settings.frontend_dist.parent / "secret.txt").write_text("secret", encoding="utf-8")

    response = client.get("/..%2Fsecret.txt")

    assert "secret" not in response.text


def test_missing_build_explains_what_to_do(tmp_path: Path) -> None:
    settings = Settings(data_dir=tmp_path / "data", frontend_dist=tmp_path / "missing")

    with TestClient(create_app(settings)) as client:
        response = client.get("/")

    assert response.status_code == 503
    assert "just build" in response.text
