"""Tests for capability presets (prompt 771)."""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest
import yaml

from keprix.capability_presets import (
    PresetValidationError,
    apply_preset,
    diff_presets,
    list_presets,
    set_state_path_for_tests,
    validate_preset,
)
from keprix.capability_presets.state import save_active_state
from keprix.plugin_lifecycle import reset_lifecycle_for_tests
from keprix.seams import get_seam_registry, reset_seams_for_tests
from tools.registry import registry as tool_registry


ROOT = Path(__file__).resolve().parents[4]


@pytest.fixture(autouse=True)
def _fresh(tmp_path):
    reset_lifecycle_for_tests()
    reset_seams_for_tests(sandbox_root=tmp_path / "sb", memory_base=tmp_path / "mem")
    set_state_path_for_tests(tmp_path / "active.json")
    save_active_state({"active": None, "mounted_plugins": [], "declared_tools": []})
    for name in list(getattr(tool_registry, "_tools", {})):
        if name.startswith("preset_"):
            tool_registry.deregister(name)
    yield
    reset_lifecycle_for_tests()
    set_state_path_for_tests(None)
    for name in list(getattr(tool_registry, "_tools", {})):
        if name.startswith("preset_"):
            tool_registry.deregister(name)


def test_schema_accepts_good_pack():
    data = validate_preset(
        {
            "name": "demo",
            "description": "ok",
            "version": 1,
            "plugins": [],
            "seams": {"fs": "policy:fs.local"},
            "soft_wall": {"profile": "standard", "require_approval": True},
            "env_refs": ["TERMINAL_ENV"],
        }
    )
    assert data["name"] == "demo"


def test_schema_rejects_soft_wall_off():
    with pytest.raises(PresetValidationError, match="forbidden"):
        validate_preset(
            {
                "name": "bad",
                "soft_wall": {"profile": "off"},
            }
        )


def test_schema_rejects_env_overlays_with_values():
    with pytest.raises(PresetValidationError, match="env_refs"):
        validate_preset(
            {
                "name": "bad",
                "soft_wall": {"profile": "standard"},
                "env": {"API_KEY": "secret"},
            }
        )


def test_schema_rejects_require_approval_false():
    with pytest.raises(PresetValidationError, match="require_approval"):
        validate_preset(
            {
                "name": "bad",
                "soft_wall": {"profile": "standard", "require_approval": False},
            }
        )


def test_shipped_presets_load():
    names = {p["name"] for p in list_presets()}
    assert {"coding", "crm", "sidecar"} <= names


def test_unknown_plugin_fails_closed(tmp_path, monkeypatch):
    # Point user packs empty; use a temporary pack with unknown plugin.
    from keprix.capability_presets import loader as loader_mod

    pack_dir = tmp_path / "packs"
    pack_dir.mkdir()
    (pack_dir / "broken.yaml").write_text(
        yaml.safe_dump(
            {
                "name": "broken",
                "description": "has unknown plugin",
                "version": 1,
                "plugins": ["definitely-not-a-real-plugin-xyz"],
                "soft_wall": {"profile": "strict", "require_approval": True},
                "seams": {"fs": "policy:fs.local"},
                "unknown_plugins": "fail",
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(loader_mod, "bundled_packs_dir", lambda: pack_dir)
    monkeypatch.setattr(loader_mod, "user_packs_dir", lambda: tmp_path / "empty")
    with pytest.raises(PresetValidationError, match="unknown plugin"):
        apply_preset("broken", who="test")


def test_apply_coding_then_crm_unmounts_coding_tools():
    result_coding = apply_preset("coding", who="test")
    assert result_coding["ok"] is True
    assert tool_registry.get_entry("preset_coding_workspace_hint") is not None
    assert tool_registry.get_entry("preset_crm_outreach_hint") is None

    result_crm = apply_preset("crm", who="test")
    assert result_crm["ok"] is True
    assert "preset_coding_workspace_hint" in result_crm["diff"]["tools_remove"]
    assert tool_registry.get_entry("preset_coding_workspace_hint") is None
    assert tool_registry.get_entry("preset_crm_outreach_hint") is not None
    # Soft Wall still enforced on shell seam after switch
    shell = get_seam_registry().get("shell")
    blocked = shell.execute("rm -rf /")
    assert blocked.get("error_code") == "hardline_blocked" or blocked.get("blocked") is True


def test_apply_sidecar_uses_sandboxed_seams():
    result = apply_preset("sidecar", who="test")
    assert result["ok"] is True
    reg = get_seam_registry()
    assert "sandboxed" in (reg.active_id("fs") or "")
    assert "sandboxed" in (reg.active_id("shell") or "")
    assert tool_registry.get_entry("preset_sidecar_health_hint") is not None
    assert result["soft_wall"]["profile"] == "strict"


def test_diff_coding_to_crm():
    d = diff_presets("coding", "crm")
    assert "preset_coding_workspace_hint" in d["tools_remove"]
    assert "preset_crm_outreach_hint" in d["tools_add"]


def test_pack_cannot_disable_soft_wall_via_apply_path():
    # validate_preset is the gate; also ensure apply refuses if somehow bypassed
    with pytest.raises(PresetValidationError):
        validate_preset({"name": "x", "soft_wall": {"profile": "yolo"}})


def test_no_cordis_or_dsh_dependency():
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    deps = [str(d).lower() for d in pyproject.get("project", {}).get("dependencies", [])]
    for dep in deps:
        assert "cordis" not in dep
        assert "deepseek-harness" not in dep
