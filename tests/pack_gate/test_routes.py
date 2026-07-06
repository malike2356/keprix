"""Pack gate API route tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from keprix.hub.manifests import PackManifest
from keprix.hub.registry import PackRegistry
from keprix.hub.routes import router as hub_router
from keprix.pack_gate.routes import router as pack_gate_router
from keprix.pack_gate.store import reset_pack_gate_store


@pytest.fixture()
def api_app():
    app = FastAPI()
    app.include_router(hub_router)
    app.include_router(pack_gate_router)
    return app


def _write_catalog_pack(catalog_root: Path, manifest: PackManifest) -> Path:
    pack_dir = catalog_root / manifest.name
    pack_dir.mkdir(parents=True, exist_ok=True)
    for rel in manifest.files:
        target = pack_dir / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("ok", encoding="utf-8")
    (pack_dir / "manifest.json").write_text(json.dumps(manifest.to_dict()), encoding="utf-8")
    return pack_dir


@pytest.fixture()
def hub_env(tmp_path, monkeypatch):
    monkeypatch.setenv("KEPRIX_API_TOKEN", "test-api-token")
    monkeypatch.setenv("KEPRIX_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("AUTH_ENABLED", "false")
    monkeypatch.setattr("keprix.pack_gate.store.get_session_factory", lambda: None)
    import keprix.hub.registry as registry_module

    registry_module._registry = PackRegistry(base_dir=tmp_path / "hub")
    reset_pack_gate_store()
    catalog_root = tmp_path / "packages" / "packs"
    catalog_root.mkdir(parents=True)
    manifest = PackManifest(
        name="clinical-pack",
        version="1.1.0",
        type="skill_pack",
        author="test",
        license="MIT",
        files=["skill.md"],
        uninstall_plan=["remove skill.md"],
        changelog={"1.1.0": "Updated hazard schema."},
        trust_label="official",
    )
    _write_catalog_pack(catalog_root, manifest)
    monkeypatch.setattr(
        "keprix.hub.registry.repo_packages_root",
        lambda: tmp_path / "packages",
    )
    return tmp_path
async def test_install_returns_202_when_gate_enabled(hub_env, api_app) -> None:
    headers = {"Authorization": "Bearer test-api-token"}
    async with AsyncClient(transport=ASGITransport(app=api_app), base_url="http://test") as client:
        put = await client.put(
            "/api/pack-gate/config",
            headers=headers,
            json={
                "enabled": True,
                "approver_user_id": "local",
                "notify_on_install": False,
                "require_changelog": True,
            },
        )
        assert put.status_code == 200

        installed = await client.post(
            "/api/hub/install",
            headers=headers,
            json={"name": "clinical-pack", "approved": True},
        )
        assert installed.status_code == 202
        payload = installed.json()
        assert payload["gate_required"] is True
        assert payload["gate_record_id"]
        assert payload["pack"]["enabled"] is False


@pytest.mark.asyncio
async def test_approve_activates_pack(hub_env, api_app) -> None:
    headers = {"Authorization": "Bearer test-api-token"}
    async with AsyncClient(transport=ASGITransport(app=api_app), base_url="http://test") as client:
        await client.put(
            "/api/pack-gate/config",
            headers=headers,
            json={
                "enabled": True,
                "approver_user_id": "local",
                "notify_on_install": False,
                "require_changelog": True,
            },
        )
        installed = await client.post(
            "/api/hub/install",
            headers=headers,
            json={"name": "clinical-pack", "approved": True},
        )
        record_id = installed.json()["gate_record_id"]
        approve = await client.post(
            f"/api/pack-gate/records/{record_id}/approve",
            headers=headers,
            json={"note": "Approved for production"},
        )
        assert approve.status_code == 200
        assert approve.json()["status"] == "approved"

        installed_list = await client.get("/api/hub/installed", headers=headers)
        pack = next(row for row in installed_list.json()["installed"] if row["name"] == "clinical-pack")
        assert pack["enabled"] is True


@pytest.mark.asyncio
async def test_missing_changelog_rejected_with_422(hub_env, tmp_path, api_app) -> None:
    catalog_root = tmp_path / "packages" / "packs"
    catalog_root.mkdir(parents=True, exist_ok=True)
    manifest = PackManifest(
        name="no-changelog-pack",
        version="1.0.0",
        type="skill_pack",
        author="test",
        license="MIT",
        files=["skill.md"],
        uninstall_plan=["remove skill.md"],
        trust_label="official",
    )
    _write_catalog_pack(catalog_root, manifest)
    headers = {"Authorization": "Bearer test-api-token"}
    async with AsyncClient(transport=ASGITransport(app=api_app), base_url="http://test") as client:
        await client.put(
            "/api/pack-gate/config",
            headers=headers,
            json={
                "enabled": True,
                "approver_user_id": "local",
                "notify_on_install": False,
                "require_changelog": True,
            },
        )
        response = await client.post(
            "/api/hub/install",
            headers=headers,
            json={"name": "no-changelog-pack", "approved": True},
        )
        assert response.status_code == 422


@pytest.mark.asyncio
async def test_reject_leaves_pack_disabled(hub_env, api_app) -> None:
    headers = {"Authorization": "Bearer test-api-token"}
    async with AsyncClient(transport=ASGITransport(app=api_app), base_url="http://test") as client:
        await client.put(
            "/api/pack-gate/config",
            headers=headers,
            json={
                "enabled": True,
                "approver_user_id": "local",
                "notify_on_install": False,
                "require_changelog": True,
            },
        )
        installed = await client.post(
            "/api/hub/install",
            headers=headers,
            json={"name": "clinical-pack", "approved": True},
        )
        record_id = installed.json()["gate_record_id"]
        rejected = await client.post(
            f"/api/pack-gate/records/{record_id}/reject",
            headers=headers,
            json={"note": "Not ready"},
        )
        assert rejected.status_code == 200
        assert rejected.json()["status"] == "rejected"
        installed_list = await client.get("/api/hub/installed", headers=headers)
        pack = next(row for row in installed_list.json()["installed"] if row["name"] == "clinical-pack")
        assert pack["enabled"] is False
