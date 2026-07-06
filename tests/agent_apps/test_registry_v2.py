"""Registry v2 install lifecycle tests."""

import shutil
from pathlib import Path

import pytest

from keprix.agent_apps.app_manifest import ManifestValidationError
from keprix.agent_apps.deployment_bundle import build_deployment_bundle
from keprix.agent_apps.registry import AgentAppRegistry, sample_app_dir


def test_registry_tracks_source_metadata(tmp_path: Path) -> None:
    registry = AgentAppRegistry(base_dir=tmp_path / "registry")
    installed = registry.install(sample_app_dir(), source="template", source_id="hello-agent")
    assert installed["source"] == "template"
    assert installed["source_id"] == "hello-agent"
    assert installed["installed_at"]
    assert "path" not in installed


def test_registry_rejects_install_outside_apps_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    registry = AgentAppRegistry(base_dir=tmp_path / "registry")
    apps_root = tmp_path / "registry" / "apps"
    outside = tmp_path / "outside"
    outside.mkdir()
    manifest_dir = sample_app_dir()
    monkeypatch.chdir(tmp_path)

    row = registry.get_internal("hello-agent")
    registry._apps.clear()
    fake_dest = outside / "hello-agent"
    fake_dest.mkdir()
    registry._apps["hello-agent"] = {
        "name": "hello-agent",
        "version": "0.1.0",
        "path": str(fake_dest),
        "installed_at": "2020-01-01T00:00:00+00:00",
        "source": "path",
        "source_id": None,
    }
    with pytest.raises(ManifestValidationError, match="outside"):
        registry.uninstall("hello-agent")

    registry._apps.clear()
    registry.install(manifest_dir, source="path")
    installed_path = registry.app_dir("hello-agent")
    assert installed_path is not None
    assert str(installed_path).startswith(str(apps_root.resolve()))


def test_registry_atomic_upgrade(tmp_path: Path) -> None:
    registry = AgentAppRegistry(base_dir=tmp_path / "registry")
    registry.install(sample_app_dir(), source="template", source_id="hello-agent")
    upgraded_source = tmp_path / "hello-agent-v2"
    shutil.copytree(sample_app_dir(), upgraded_source)
    manifest = (upgraded_source / "agent.yaml").read_text(encoding="utf-8")
    (upgraded_source / "agent.yaml").write_text(
        manifest.replace("version: 1.0.0", "version: 1.1.0"),
        encoding="utf-8",
    )

    app = registry.upgrade("hello-agent", upgraded_source, source="upload")
    assert app["version"] == "1.1.0"
    assert app["source"] == "upload"
    assert registry.app_dir("hello-agent") is not None
    assert (registry.app_dir("hello-agent") / "agent.yaml").read_text(encoding="utf-8").find("1.1.0") >= 0


def test_registry_upgrade_name_mismatch(tmp_path: Path) -> None:
    registry = AgentAppRegistry(base_dir=tmp_path / "registry")
    registry.install(sample_app_dir(), source="template", source_id="hello-agent")
    other = tmp_path / "other-app"
    shutil.copytree(sample_app_dir(), other)
    (other / "agent.yaml").write_text(
        (other / "agent.yaml").read_text(encoding="utf-8").replace("hello-agent", "other-app"),
        encoding="utf-8",
    )
    with pytest.raises(ManifestValidationError, match="does not match"):
        registry.upgrade("hello-agent", other)


def test_install_from_zip_bytes(tmp_path: Path) -> None:
    registry = AgentAppRegistry(base_dir=tmp_path / "registry")
    bundle = tmp_path / "hello-agent.zip"
    build_deployment_bundle(sample_app_dir(), bundle)
    app = registry.install_from_zip_bytes(bundle.read_bytes(), source="upload", source_id="hello-agent.zip")
    assert app["name"] == "hello-agent"
    assert registry.get("hello-agent") is not None
