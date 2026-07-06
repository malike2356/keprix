"""Zip upload install route tests."""

import io
import shutil
import zipfile
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from keprix.agent_apps.deployment_bundle import build_deployment_bundle
from keprix.agent_apps.registry import AgentAppRegistry, sample_app_dir
from keprix.agent_apps.routes import router as agent_apps_router
from keprix.api.auth import require_api_auth


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    from keprix.agent_apps import registry as registry_module

    monkeypatch.setattr(registry_module, "_registry", AgentAppRegistry(base_dir=tmp_path / "registry"))
    app = FastAPI()
    app.include_router(agent_apps_router)

    async def _fake_auth() -> str:
        return "test-user"

    async def _allow_entitlement(*_args, **_kwargs) -> None:
        return None

    async def _noop_audit(*_args, **_kwargs) -> None:
        return None

    app.dependency_overrides[require_api_auth] = _fake_auth
    monkeypatch.setattr("keprix.agent_apps.routes.assert_can_run", _allow_entitlement)
    monkeypatch.setattr("keprix.agent_apps.routes.assert_can_install", _allow_entitlement)
    monkeypatch.setattr("keprix.agent_apps.routes.assert_can_install_catalog_template", _allow_entitlement)
    monkeypatch.setattr("keprix.agent_apps.routes.audit_log", _noop_audit)
    return TestClient(app)


def _bundle_bytes(tmp_path: Path) -> bytes:
    bundle = tmp_path / "hello-agent.zip"
    build_deployment_bundle(sample_app_dir(), bundle)
    return bundle.read_bytes()


def test_install_upload(client: TestClient, tmp_path: Path) -> None:
    response = client.post(
        "/api/agent-apps/install/upload",
        files={"file": ("hello-agent.zip", _bundle_bytes(tmp_path), "application/zip")},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["app"]["name"] == "hello-agent"
    assert body["redirect"] == "/agent-apps/hello-agent"
    listed = client.get("/api/agent-apps").json()["apps"]
    assert any(item["name"] == "hello-agent" for item in listed)


def test_validate_upload(client: TestClient, tmp_path: Path) -> None:
    response = client.post(
        "/api/agent-apps/validate/upload",
        files={"file": ("hello-agent.zip", _bundle_bytes(tmp_path), "application/zip")},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["valid"] is True
    assert body["manifest"]["name"] == "hello-agent"


def test_upload_rejects_path_traversal(client: TestClient, tmp_path: Path) -> None:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("../evil.txt", "bad")
        archive.writestr(
            "hello-agent/agent.yaml",
            (sample_app_dir() / "agent.yaml").read_text(encoding="utf-8"),
        )
    response = client.post(
        "/api/agent-apps/validate/upload",
        files={"file": ("evil.zip", buffer.getvalue(), "application/zip")},
    )
    assert response.status_code == 200
    assert response.json()["valid"] is False


def test_uninstall_removes_app(client: TestClient, tmp_path: Path) -> None:
    client.post("/api/agent-apps/catalog/daily-standup/install")
    response = client.delete("/api/agent-apps/daily-standup")
    assert response.status_code == 200
    assert client.get("/api/agent-apps/daily-standup").status_code == 404


def test_export_download(client: TestClient, tmp_path: Path) -> None:
    client.post(
        "/api/agent-apps/install/upload",
        files={"file": ("hello-agent.zip", _bundle_bytes(tmp_path), "application/zip")},
    )
    response = client.get("/api/agent-apps/hello-agent/export")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/zip")
    assert len(response.content) > 100


def test_upgrade_upload(client: TestClient, tmp_path: Path) -> None:
    client.post(
        "/api/agent-apps/install/upload",
        files={"file": ("hello-agent.zip", _bundle_bytes(tmp_path), "application/zip")},
    )
    upgraded = tmp_path / "hello-agent-v2"
    shutil.copytree(sample_app_dir(), upgraded)
    manifest = (upgraded / "agent.yaml").read_text(encoding="utf-8")
    (upgraded / "agent.yaml").write_text(
        manifest.replace("version: 1.0.0", "version: 1.1.0"),
        encoding="utf-8",
    )
    bundle = tmp_path / "upgrade.zip"
    build_deployment_bundle(upgraded, bundle)
    response = client.post(
        "/api/agent-apps/hello-agent/upgrade",
        files={"file": ("upgrade.zip", bundle.read_bytes(), "application/zip")},
    )
    assert response.status_code == 200
    assert response.json()["app"]["version"] == "1.1.0"


def test_path_install_requires_dev_mode(client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("KEPRIX_DEV_MODE", raising=False)

    async def _non_admin_auth() -> str:
        return "regular-user"

    client.app.dependency_overrides[require_api_auth] = _non_admin_auth
    response = client.post("/api/agent-apps/install", json={"path": str(sample_app_dir())})
    assert response.status_code == 403
