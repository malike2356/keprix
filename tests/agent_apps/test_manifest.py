"""Agent app manifest tests."""

from pathlib import Path

import pytest

from keprix.agent_apps.app_manifest import ManifestValidationError, load_manifest, validate_manifest
from keprix.agent_apps.registry import sample_app_dir


def _write_minimal_app(app_dir: Path, agent_yaml: str) -> None:
    app_dir.mkdir(parents=True, exist_ok=True)
    (app_dir / "agent.yaml").write_text(agent_yaml, encoding="utf-8")
    (app_dir / "instructions.md").write_text("instructions", encoding="utf-8")
    (app_dir / "README.md").write_text("readme", encoding="utf-8")
    agents = app_dir / "agents"
    agents.mkdir()
    (agents / "main.py").write_text(
        "def run(input_text, context=None):\n"
        "    return {'status': 'ok', 'output': input_text, 'form': (context or {}).get('form')}\n",
        encoding="utf-8",
    )


def test_sample_manifest_loads_v2_fields() -> None:
    manifest = load_manifest(sample_app_dir())
    assert manifest.name == "hello-agent"
    assert manifest.display_name == "Hello Agent"
    assert manifest.version == "1.0.0"
    assert manifest.eval_suite == "evals/basic.yaml"
    assert manifest.inputs[0].id == "name"
    assert manifest.outputs[0].type == "text"


def test_v1_manifest_defaults() -> None:
    app_dir = Path(__file__).resolve().parents[2] / "src" / "keprix" / "agent_apps" / "sample" / "hello_agent"
    manifest = load_manifest(app_dir)
    assert manifest.display_name
    assert manifest.category == "custom"
    assert isinstance(manifest.inputs, list)


def test_manifest_rejects_missing_entrypoint(tmp_path: Path) -> None:
    app_dir = tmp_path / "broken"
    app_dir.mkdir()
    (app_dir / "agent.yaml").write_text("name: broken\nversion: 0.1.0\n", encoding="utf-8")
    (app_dir / "instructions.md").write_text("x", encoding="utf-8")
    (app_dir / "README.md").write_text("x", encoding="utf-8")
    with pytest.raises(ManifestValidationError):
        load_manifest(app_dir)


def test_manifest_rejects_invalid_name(tmp_path: Path) -> None:
    _write_minimal_app(
        tmp_path / "bad-name",
        "name: Bad_Name\nversion: 1.0.0\nentrypoint: agents.main:run\n",
    )
    with pytest.raises(ManifestValidationError):
        load_manifest(tmp_path / "bad-name")


def test_manifest_rejects_duplicate_input_ids(tmp_path: Path) -> None:
    _write_minimal_app(
        tmp_path / "dup-inputs",
        """
name: dup-inputs
version: 1.0.0
entrypoint: agents.main:run
inputs:
  - id: focus
    label: One
    type: text
  - id: focus
    label: Two
    type: text
""".strip(),
    )
    with pytest.raises(ManifestValidationError):
        load_manifest(tmp_path / "dup-inputs")


def test_manifest_rejects_select_without_options(tmp_path: Path) -> None:
    _write_minimal_app(
        tmp_path / "select-missing",
        """
name: select-missing
version: 1.0.0
entrypoint: agents.main:run
inputs:
  - id: mode
    label: Mode
    type: select
""".strip(),
    )
    with pytest.raises(ManifestValidationError):
        load_manifest(tmp_path / "select-missing")


def test_manifest_accepts_v2_output_types(tmp_path: Path) -> None:
    _write_minimal_app(
        tmp_path / "outputs",
        """
name: outputs-app
version: 1.0.0
display_name: Outputs App
description: Test outputs
category: research
runtime: python
entrypoint: agents.main:run
inputs:
  - id: topic
    label: Topic
    type: textarea
outputs:
  - id: markdown
    type: markdown
""".strip(),
    )
    manifest = load_manifest(tmp_path / "outputs")
    summary = manifest.summary_dict()
    assert summary["display_name"] == "Outputs App"
    assert summary["inputs"][0]["type"] == "textarea"
    assert summary["outputs"][0]["type"] == "markdown"
    assert "app_dir" not in summary
