"""Built app API route tests."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from keprix.api.auth import require_api_auth
from keprix.built_apps.routes import router as built_apps_router

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("KEPRIX_DATA_DIR", str(tmp_path))
    app_dir = tmp_path / "built_apps" / "starter"
    app_dir.mkdir(parents=True)
    app_dir.joinpath("built_app.yaml").write_text(
        (ROOT / "examples/built-app-starter/built_app.yaml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    app = FastAPI()
    app.include_router(built_apps_router)

    async def _fake_auth() -> str:
        return "test-user"

    app.dependency_overrides[require_api_auth] = _fake_auth
    return TestClient(app)


def test_list_built_apps(client: TestClient) -> None:
    response = client.get("/api/built-apps")
    assert response.status_code == 200
    app = response.json()["apps"][0]
    assert app["id"] == "starter"
    assert "navigation" not in app


def test_get_built_app_detail(client: TestClient) -> None:
    response = client.get("/api/built-apps/starter")
    assert response.status_code == 200
    app = response.json()["app"]
    assert app["id"] == "starter"
    assert app["navigation"]["items"][1]["href"] == "/apps/starter/reports"


def test_get_unknown_built_app(client: TestClient) -> None:
    response = client.get("/api/built-apps/missing")
    assert response.status_code == 404
