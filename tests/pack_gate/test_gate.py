"""Pack gate enforcement unit tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from keprix.hub.installer import install_pack
from keprix.hub.manifests import PackManifest
from keprix.hub.registry import PackRegistry
from keprix.pack_gate.gate import changelog_for_version, validate_manifest_changelog
from keprix.pack_gate.service import after_pack_install, approve_record
from keprix.pack_gate.store import get_pack_gate_store, reset_pack_gate_store


def _write_pack(tmp_path: Path, manifest: PackManifest) -> Path:
    pack_dir = tmp_path / manifest.name
    pack_dir.mkdir()
    for rel in manifest.files:
        target = pack_dir / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("ok", encoding="utf-8")
    (pack_dir / "manifest.json").write_text(json.dumps(manifest.to_dict()), encoding="utf-8")
    return pack_dir


@pytest.fixture()
def registry(tmp_path, monkeypatch):
    monkeypatch.setenv("KEPRIX_DATA_DIR", str(tmp_path))
    import keprix.hub.registry as registry_module

    reg = PackRegistry(base_dir=tmp_path / "hub")
    registry_module._registry = reg
    reset_pack_gate_store()
    return reg


@pytest.fixture()
def gate_env(tmp_path, monkeypatch):
    monkeypatch.setenv("KEPRIX_DATA_DIR", str(tmp_path))
    monkeypatch.setattr("keprix.pack_gate.store.get_session_factory", lambda: None)
    reset_pack_gate_store()
    return get_pack_gate_store()


@pytest.mark.asyncio
async def test_changelog_required_when_configured() -> None:
    manifest = PackManifest(
        name="clinical-pack",
        version="1.0.0",
        type="skill_pack",
        author="test",
        license="MIT",
        files=["skill.md"],
        uninstall_plan=["remove skill.md"],
    )
    with pytest.raises(ValueError, match="missing changelog"):
        validate_manifest_changelog(manifest, require=True)

    manifest.changelog = {"1.0.0": "Initial regulated release."}
    assert changelog_for_version(manifest) == "Initial regulated release."


@pytest.mark.asyncio
async def test_gate_blocks_activation_until_approved(registry, gate_env, tmp_path) -> None:
    await gate_env.save_config(
        "default",
        {
            "enabled": True,
            "approver_user_id": "approver-1",
            "approver_email": "cso@example.com",
            "notify_on_install": False,
            "require_changelog": False,
        },
    )
    manifest = PackManifest(
        name="gated-pack",
        version="1.0.0",
        type="skill_pack",
        author="test",
        license="MIT",
        files=["skill.md"],
        uninstall_plan=["remove skill.md"],
        trust_label="official",
        changelog={"1.0.0": "First release"},
    )
    pack_dir = _write_pack(tmp_path, manifest)
    result = install_pack(pack_dir, manifest, approved=True, enabled=False)
    assert result["status"] == "installed"
    assert registry.get_installed("gated-pack").enabled is False

    gate_info = await after_pack_install(
        workspace_id="default",
        manifest=manifest,
        requested_by_user_id="installer-1",
        from_version=None,
    )
    assert gate_info is not None
    assert gate_info["gate_required"] is True

    record_id = gate_info["gate_record_id"]
    approved = await approve_record(
        workspace_id="default",
        record_id=record_id,
        actor={"id": "approver-1", "role": "user"},
        note="Reviewed changelog",
    )
    assert approved["status"] == "approved"
    assert registry.get_installed("gated-pack").enabled is True


@pytest.mark.asyncio
async def test_gate_disabled_allows_immediate_activation(registry, gate_env, tmp_path) -> None:
    await gate_env.save_config(
        "default",
        {
            "enabled": False,
            "approver_user_id": None,
            "approver_email": None,
            "notify_on_install": True,
            "require_changelog": True,
        },
    )
    manifest = PackManifest(
        name="open-pack",
        version="1.0.0",
        type="skill_pack",
        author="test",
        license="MIT",
        files=["skill.md"],
        uninstall_plan=["remove skill.md"],
        trust_label="official",
    )
    pack_dir = _write_pack(tmp_path, manifest)
    result = install_pack(pack_dir, manifest, approved=True, enabled=True)
    assert result["status"] == "installed"
    gate_info = await after_pack_install(
        workspace_id="default",
        manifest=manifest,
        requested_by_user_id="installer-1",
        from_version=None,
    )
    assert gate_info is None
    assert registry.get_installed("open-pack").enabled is True
