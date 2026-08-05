"""Tests for n8n workflow to playbook conversion (Prompt 207)."""

from __future__ import annotations

import json
from argparse import Namespace
from pathlib import Path

import yaml

from keprix.backend.migration.cli import cmd_migrate_from_n8n
from keprix.backend.migration.n8n_converter import convert_n8n_workflow, load_n8n_export

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "n8n"


def _load_fixture(name: str) -> dict:
    return load_n8n_export(FIXTURES / name)


def test_http_workflow_maps_http_step_and_entry() -> None:
    result = convert_n8n_workflow(_load_fixture("simple_http.json"))
    doc = yaml.safe_load("\n".join(line for line in result.yaml_text.splitlines() if not line.startswith("#")))
    http_steps = [step for step in doc["steps"] if step["type"] == "http"]
    assert len(http_steps) == 1
    assert http_steps[0]["url"] == "http://mock-api.com/data"
    assert http_steps[0]["query"] == {"test": "1"}
    assert doc.get("entry") == http_steps[0]["id"]


def test_if_node_produces_condition_step() -> None:
    result = convert_n8n_workflow(_load_fixture("if_code_chain.json"))
    doc = yaml.safe_load("\n".join(line for line in result.yaml_text.splitlines() if not line.startswith("#")))
    condition_steps = [step for step in doc["steps"] if step["type"] == "condition"]
    assert len(condition_steps) == 1
    assert "n8n_expr" in condition_steps[0]["expression"] or "lt" in condition_steps[0]["expression"]


def test_code_node_preserves_source_text() -> None:
    result = convert_n8n_workflow(_load_fixture("if_code_chain.json"))
    doc = yaml.safe_load("\n".join(line for line in result.yaml_text.splitlines() if not line.startswith("#")))
    code_steps = [step for step in doc["steps"] if step["type"] == "code" and step.get("language") == "javascript"]
    assert len(code_steps) == 1
    assert "Array.from" in code_steps[0]["source"]


def test_unknown_node_type_is_skipped_but_yaml_valid() -> None:
    result = convert_n8n_workflow(_load_fixture("if_code_chain.json"))
    skipped = [row for row in result.skipped_nodes if row["type"] == "n8n-nodes-base.slack"]
    assert len(skipped) == 1
    assert skipped[0]["reason"] == "unsupported_node_type"
    doc = yaml.safe_load("\n".join(line for line in result.yaml_text.splitlines() if not line.startswith("#")))
    assert isinstance(doc["steps"], list)
    assert "# Skipped nodes:" in result.yaml_text


def test_edges_include_code_to_if_link() -> None:
    result = convert_n8n_workflow(_load_fixture("if_code_chain.json"))
    doc = yaml.safe_load("\n".join(line for line in result.yaml_text.splitlines() if not line.startswith("#")))
    assert any(edge["from"] == "code" and edge["to"] == "if" for edge in doc["edges"])


def test_cli_dry_run_exits_zero(capsys) -> None:
    code = cmd_migrate_from_n8n(
        Namespace(
            source=str(FIXTURES / "simple_http.json"),
            output=None,
            output_dir=None,
            id=None,
            dry_run=True,
            report=False,
        )
    )
    captured = capsys.readouterr()
    assert code == 0
    assert "Converted 'Simple HTTP workflow'" in captured.out
    assert "type: http" in captured.out


def test_cli_writes_output_and_report(tmp_path) -> None:
    output = tmp_path / "imported.yml"
    code = cmd_migrate_from_n8n(
        Namespace(
            source=str(FIXTURES / "simple_http.json"),
            output=str(output),
            output_dir=None,
            id="simple-http",
            dry_run=False,
            report=True,
        )
    )
    assert code == 0
    assert output.exists()
    report = tmp_path / "simple-http.migration-report.json"
    assert report.exists()
    payload = json.loads(report.read_text(encoding="utf-8"))
    assert payload["playbook_id"] == "simple-http"
