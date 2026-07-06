"""Hub installer and rollback tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from keprix.api.main import app
from keprix.hub.installer import install_pack, rollback_pack, uninstall_pack
from keprix.hub.manifests import PackManifest
from keprix.hub.registry import PackRegistry


def _write_pack(tmp_path: Path, manifest: PackManifest, *, secret: str | None = None) -> Path:
    pack_dir = tmp_path / manifest.name
    pack_dir.mkdir()
    for rel in manifest.files:
        target = pack_dir / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        if secret and rel.endswith(".env"):
            target.write_text(secret, encoding="utf-8")
        else:
            target.write_text("ok", encoding="utf-8")
    (pack_dir / "manifest.json").write_text(json.dumps(manifest.to_dict()), encoding="utf-8")
    return pack_dir


@pytest.fixture()
def registry(tmp_path, monkeypatch):
    monkeypatch.setenv("KEPRIX_DATA_DIR", str(tmp_path))
    import keprix.hub.registry as registry_module

    reg = PackRegistry(base_dir=tmp_path / "hub")
    registry_module._registry = reg
    return reg


def test_valid_pack_install(registry, tmp_path) -> None:
    manifest = PackManifest(
        name="demo-pack",
        version="1.0.0",
        type="skill_pack",
        author="test",
        license="MIT",
        files=["skills/demo/SKILL.md"],
        uninstall_plan=["remove skills/demo"],
        trust_label="official",
    )
    pack_dir = _write_pack(tmp_path, manifest)
    result = install_pack(pack_dir, manifest, approved=True)
    assert result["status"] == "installed"
    assert registry.get_installed("demo-pack") is not None


def test_secret_pack_fails(registry, tmp_path) -> None:
    manifest = PackManifest(
        name="secret-pack",
        version="1.0.0",
        type="skill_pack",
        author="test",
        license="MIT",
        files=["secrets.env"],
        uninstall_plan=["remove secrets.env"],
        trust_label="official",
    )
    pack_dir = _write_pack(tmp_path, manifest, secret='TOKEN="sk-abcdefghijklmnopqrstuvwxyz1234"')
    result = install_pack(pack_dir, manifest, approved=True)
    assert result["status"] == "error"


def test_risky_pack_requires_approval(registry, tmp_path) -> None:
    manifest = PackManifest(
        name="risky-pack",
        version="1.0.0",
        type="connector_pack",
        author="test",
        license="MIT",
        files=["connector.yaml"],
        uninstall_plan=["remove connector.yaml"],
        risk_level="high",
        permissions=["network:egress"],
        trust_label="official",
    )
    pack_dir = _write_pack(tmp_path, manifest)
    pending = install_pack(pack_dir, manifest, approved=False)
    assert pending["status"] == "awaiting_approval"
    installed = install_pack(pack_dir, manifest, approved=True)
    assert installed["status"] == "installed"


def test_invalid_manifest_install_fails(registry, tmp_path) -> None:
    manifest = PackManifest(
        name="",
        version="",
        type="unknown",
        author="test",
        license="MIT",
        files=[],
        uninstall_plan=[],
    )
    pack_dir = tmp_path / "bad"
    pack_dir.mkdir()
    (pack_dir / "manifest.json").write_text("{}", encoding="utf-8")
    result = install_pack(pack_dir, manifest, approved=True)
    assert result["status"] == "error"


def test_update_preserves_snapshot_and_rollback(registry, tmp_path) -> None:
    manifest_v1 = PackManifest(
        name="versioned-pack",
        version="1.0.0",
        type="skill_pack",
        author="test",
        license="MIT",
        files=["content.txt"],
        uninstall_plan=["remove content.txt"],
        trust_label="official",
    )
    pack_dir = _write_pack(tmp_path, manifest_v1)
    (pack_dir / "content.txt").write_text("v1", encoding="utf-8")
    install_pack(pack_dir, manifest_v1, approved=True)

    manifest_v2 = PackManifest(
        name="versioned-pack",
        version="2.0.0",
        type="skill_pack",
        author="test",
        license="MIT",
        files=["content.txt"],
        uninstall_plan=["remove content.txt"],
        trust_label="official",
    )
    (pack_dir / "content.txt").write_text("v2", encoding="utf-8")
    install_pack(pack_dir, manifest_v2, approved=True)
    assert registry.get_installed("versioned-pack").version == "2.0.0"

    rolled = rollback_pack("versioned-pack", "1.0.0")
    assert rolled["status"] == "rolled_back"
    install_path = Path(registry.get_installed("versioned-pack").install_path)
    assert (install_path / "content.txt").read_text(encoding="utf-8") == "v1"


@pytest.mark.asyncio
async def test_hub_routes_list_and_install(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("KEPRIX_API_TOKEN", "test-api-token")
    monkeypatch.setenv("KEPRIX_DATA_DIR", str(tmp_path))
    import keprix.hub.registry as registry_module

    registry_module._registry = None
    headers = {"Authorization": "Bearer test-api-token"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        listed = await client.get("/api/hub/packs", headers=headers)
        assert listed.status_code == 200
        payload = listed.json()
        assert payload["packs"]
        installed = await client.post(
            "/api/hub/install",
            headers=headers,
            json={"name": "research-helper", "approved": True},
        )
        assert installed.status_code == 200
        assert installed.json()["status"] == "installed"
