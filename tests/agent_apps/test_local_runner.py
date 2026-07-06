"""Local runner and eval tests."""

import json
import zipfile
from pathlib import Path

from keprix.agent_apps.deployment_bundle import build_deployment_bundle
from keprix.agent_apps.eval_runner import run_eval_suite
from keprix.agent_apps.local_runner import run_local
from keprix.agent_apps.registry import AgentAppRegistry, sample_app_dir


def test_sample_app_runs_from_cli() -> None:
    result = run_local(sample_app_dir(), input_text="world")
    assert result["result"]["output"] == "Hello from hello-agent: world"
    assert result["runner"] == "cli"


def test_eval_runner_executes_bundled_tests() -> None:
    report = run_eval_suite(sample_app_dir())
    assert report["success"] is True
    assert report["passed"] == 2


def test_registry_install_and_validate(tmp_path: Path) -> None:
    registry = AgentAppRegistry(tmp_path / "apps")
    validation = registry.validate_only(sample_app_dir())
    assert validation["valid"] is True
    installed = registry.install(sample_app_dir())
    assert installed["name"] == "hello-agent"


def test_deployment_bundle_excludes_secrets(tmp_path: Path) -> None:
    registry = AgentAppRegistry(tmp_path / "registry")
    registry.install(sample_app_dir())
    app_dir = registry.app_dir("hello-agent")
    assert app_dir is not None
    (app_dir / ".env").write_text("SECRET=bad\n", encoding="utf-8")
    (app_dir / "__pycache__").mkdir()
    (app_dir / "__pycache__" / "junk.pyc").write_bytes(b"bad")
    bundle_path = tmp_path / "bundle.zip"
    build_deployment_bundle(app_dir, bundle_path, target="hub")
    with zipfile.ZipFile(bundle_path) as archive:
        names = archive.namelist()
    assert ".env" not in names
    assert not any("__pycache__" in name for name in names)
    meta = json.loads(zipfile.ZipFile(bundle_path).read("bundle.json"))
    assert meta["target"] == "hub"
