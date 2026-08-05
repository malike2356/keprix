"""n8n workflow to Studio canvas import tests."""

from __future__ import annotations

import json
from pathlib import Path

from keprix.playbook.canvas_compiler import compile_canvas_document
from keprix.playbook.n8n_canvas_importer import n8n_to_canvas_warnings, n8n_workflow_to_canvas
from keprix.playbook.yaml_compiler import compile_playbook_document

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "n8n" / "minimal_workflow.json"


def test_n8n_fixture_imports_to_canvas_and_compiles() -> None:
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))

    canvas = n8n_workflow_to_canvas(payload)
    yaml_doc = compile_canvas_document(canvas)

    assert len(canvas["nodes"]) >= 2
    assert canvas["nodes"][0]["type"] == "trigger"
    assert compile_playbook_document(yaml_doc).graph_id == "imported_support_flow"


def test_n8n_import_warnings_for_unmapped_nodes() -> None:
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))

    warnings = n8n_to_canvas_warnings(payload)

    assert any("Unsupported" in warning for warning in warnings)
