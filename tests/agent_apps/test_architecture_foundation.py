"""Agent app manifest and architecture tests."""

from pathlib import Path

import pytest

from keprix.agent_apps.app_manifest import ManifestValidationError, load_manifest, validate_manifest
from keprix.agent_apps.catalog import install_catalog_template, list_catalog_templates, template_dir
from keprix.agent_apps.registry import AgentAppRegistry, sample_app_dir


def test_sample_manifest_loads_v2_fields() -> None:
    manifest = load_manifest(sample_app_dir())
    assert manifest.name == "hello-agent"
    assert manifest.display_name == "Hello Agent"
    assert manifest.runtime == "python"
    assert manifest.inputs[0].id == "name"


def test_manifest_rejects_missing_entrypoint(tmp_path: Path) -> None:
    app_dir = tmp_path / "broken"
    app_dir.mkdir()
    (app_dir / "agent.yaml").write_text("name: broken\nversion: 0.1.0\n", encoding="utf-8")
    (app_dir / "instructions.md").write_text("x", encoding="utf-8")
    (app_dir / "README.md").write_text("x", encoding="utf-8")
    with pytest.raises(ManifestValidationError):
        load_manifest(app_dir)


def test_agent_runtime_manifest_without_entrypoint(tmp_path: Path) -> None:
    source = template_dir("daily-standup")
    assert source is not None
    manifest = load_manifest(source)
    assert manifest.runtime == "agent"
    assert manifest.entrypoint == ""
    validate_manifest(manifest)


def test_catalog_lists_templates() -> None:
    templates = list_catalog_templates()
    assert len(templates) >= 3
    ids = {item["id"] for item in templates}
    assert "daily-standup" in ids


def test_registry_install_and_uninstall(tmp_path: Path) -> None:
    registry = AgentAppRegistry(base_dir=tmp_path / "registry")
    installed = registry.install(sample_app_dir(), source="template", source_id="hello-agent")
    assert installed["name"] == "hello-agent"
    assert installed["source"] == "template"
    assert "path" not in installed
    assert registry.app_dir("hello-agent") is not None
    assert registry.uninstall("hello-agent")
    assert registry.get("hello-agent") is None


def test_catalog_install_to_registry(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from keprix.agent_apps import registry as registry_module

    monkeypatch.setattr(registry_module, "_registry", AgentAppRegistry(base_dir=tmp_path / "registry"))
    app = install_catalog_template("daily-standup")
    assert app["name"] == "daily-standup"
    assert app["runtime"] == "agent"
