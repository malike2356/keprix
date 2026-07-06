"""Run payload and form merge tests."""

from pathlib import Path

from keprix.agent_apps.registry import AgentAppRegistry, sample_app_dir
from keprix.agent_apps.runner_core import run_agent_app


def _write_form_app(app_dir: Path) -> None:
    app_dir.mkdir(parents=True, exist_ok=True)
    (app_dir / "agent.yaml").write_text(
        """
name: form-app
version: 1.0.0
entrypoint: agents.main:run
inputs:
  - id: name
    label: Name
    type: text
    default: world
outputs:
  - id: text
    type: text
""".strip(),
        encoding="utf-8",
    )
    (app_dir / "instructions.md").write_text("x", encoding="utf-8")
    (app_dir / "README.md").write_text("x", encoding="utf-8")
    agents = app_dir / "agents"
    agents.mkdir()
    (agents / "main.py").write_text(
        """
def run(input_text, context=None):
    form = (context or {}).get("form") or {}
    return {
        "status": "ok",
        "output": f"Hello {form.get('name', input_text)}",
        "form": form,
    }
""".strip(),
        encoding="utf-8",
    )


def test_run_with_structured_inputs(tmp_path: Path) -> None:
    source = tmp_path / "source"
    _write_form_app(source)
    registry = AgentAppRegistry(base_dir=tmp_path / "registry")
    registry.install(source)
    app_dir = registry.app_dir("form-app")
    assert app_dir is not None
    result = run_agent_app(app_dir, input_text="", context={"form": {"name": "Keprix"}})
    assert result["result"]["output"] == "Hello Keprix"
    assert result["result"]["form"] == {"name": "Keprix"}


def test_legacy_input_maps_to_first_text_field(tmp_path: Path) -> None:
    source = tmp_path / "source"
    _write_form_app(source)
    registry = AgentAppRegistry(base_dir=tmp_path / "registry")
    registry.install(source)
    app_dir = registry.app_dir("form-app")
    assert app_dir is not None
    result = run_agent_app(app_dir, input_text="Legacy", context={})
    assert result["result"]["form"] == {"name": "Legacy"}


def test_hello_agent_uses_name_input(tmp_path: Path) -> None:
    registry = AgentAppRegistry(base_dir=tmp_path / "registry")
    registry.install(sample_app_dir())
    app_dir = registry.app_dir("hello-agent")
    assert app_dir is not None
    result = run_agent_app(app_dir, input_text="", context={"form": {"name": "Ada"}})
    assert "Ada" in result["result"]["output"]
