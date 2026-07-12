"""Prompt 264 Personal OS starter pack install tests."""

from __future__ import annotations

import json
from pathlib import Path

from httpx import ASGITransport, AsyncClient
import pytest

from keprix.api.main import app
from keprix.agent_os.headless_run_service import HeadlessRunService
from keprix.hub.installer import install_pack
from keprix.hub.manifests import PackManifest, validate_manifest
from keprix.hub.registry import PackRegistry
from keprix.hub.verifier import verify_manifest


PACK_DIR = Path("packages/packs/keprix-personal-os-starter")


@pytest.fixture
def pack_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    home = tmp_path / ".keprix"
    monkeypatch.setenv("KEPRIX_HOME", str(home))
    monkeypatch.setenv("KEPRIX_DATA_DIR", str(home))
    import keprix.hub.registry as registry_module

    registry_module._registry = PackRegistry(base_dir=home / "hub")
    return home


def _manifest() -> PackManifest:
    return PackManifest.from_dict(json.loads((PACK_DIR / "manifest.json").read_text(encoding="utf-8")))


def test_personal_os_manifest_verifies() -> None:
    manifest = _manifest()
    assert validate_manifest(manifest) == []
    assert verify_manifest(manifest)
    assert manifest.name == "keprix-personal-os-starter"


def test_personal_os_pack_install_adds_skills_workspace_audit_and_pins(pack_home: Path) -> None:
    result = install_pack(PACK_DIR, _manifest(), approved=True)

    assert result["status"] == "installed"
    assert result["post_install"]["skills"] == 6
    assert (pack_home / "skills" / "daily-brief" / "SKILL.md").exists()
    assert (pack_home / "workspaces" / "personal-os" / "index.md").exists()
    assert (pack_home / "agent-os" / "action-board.json").exists()
    assert list((pack_home / "agent-os" / "audits").glob("*.json"))


@pytest.mark.asyncio
async def test_hub_install_personal_os_pack_and_headless_pin(pack_home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KEPRIX_API_TOKEN", "test-api-token")
    import keprix.hub.registry as registry_module
    import keprix.hub.routes as hub_routes

    registry_module._registry = PackRegistry(base_dir=pack_home / "hub")
    class FakeGateStore:
        async def get_config(self, workspace_id: str) -> dict:
            return {"require_changelog": False}

    monkeypatch.setattr(hub_routes, "get_pack_gate_store", lambda: FakeGateStore())
    monkeypatch.setattr(hub_routes, "is_gate_enabled", lambda workspace_id: __import__("asyncio").sleep(0, result=False))
    monkeypatch.setattr(hub_routes, "check_changelog_or_raise", lambda *args, **kwargs: None)
    monkeypatch.setattr(hub_routes, "after_pack_install", lambda **kwargs: __import__("asyncio").sleep(0, result=None))
    headers = {"Authorization": "Bearer test-api-token"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        listed = await client.get("/api/hub/packs", headers=headers)
        assert any(pack["name"] == "keprix-personal-os-starter" for pack in listed.json()["packs"])
        installed = await client.post(
            "/api/hub/install",
            headers=headers,
            json={"name": "keprix-personal-os-starter", "approved": True},
        )
    assert installed.status_code == 200
    result = await HeadlessRunService().run_skill("daily-brief", {"workspace_id": "default"})
    assert result.status == "completed"
