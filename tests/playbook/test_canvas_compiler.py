"""Visual Playbook Studio canvas compiler tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from keprix.playbook.canvas_compiler import CanvasCompileError, compile_canvas_document
from keprix.playbook.canvas_decompiler import decompile_playbook_document
from keprix.playbook.studio_store import PlaybookStudioStore
from keprix.playbook.yaml_compiler import compile_playbook_document

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "playbooks" / "canvas"


def _fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def test_compile_simple_linear() -> None:
    yaml_doc = compile_canvas_document(_fixture("linear_three_node.json"))

    assert yaml_doc["entry"] == "summarize"
    assert [step["id"] for step in yaml_doc["steps"]] == ["summarize", "notify"]
    assert yaml_doc["edges"] == [{"from": "summarize", "to": "notify"}]
    assert compile_playbook_document(yaml_doc).graph_id == "daily_digest"


def test_compile_condition_branches() -> None:
    yaml_doc = compile_canvas_document(_fixture("condition_branch.json"))
    condition = next(step for step in yaml_doc["steps"] if step["id"] == "score")

    assert condition["expression"] == "risk_score > 70"
    assert condition["on_true"] == "approval"
    assert condition["on_false"] == "record"
    assert {"from": "score", "to": "approval", "when": "true"} in yaml_doc["edges"]
    assert {"from": "score", "to": "record", "when": "false"} in yaml_doc["edges"]
    assert compile_playbook_document(yaml_doc).graph_id == "approval_gate"


def test_compile_rejects_cycle() -> None:
    canvas = _fixture("linear_three_node.json")
    canvas["edges"].append({"id": "e_notify_summarize", "source": "notify", "target": "summarize"})

    with pytest.raises(CanvasCompileError) as exc:
        compile_canvas_document(canvas)
    assert any(error["code"] == "cycle_detected" for error in exc.value.errors)


def test_compile_rejects_duplicate_ids() -> None:
    canvas = _fixture("linear_three_node.json")
    canvas["nodes"][2]["id"] = "summarize"

    with pytest.raises(CanvasCompileError) as exc:
        compile_canvas_document(canvas)
    assert any(error["code"] == "duplicate_node_id" for error in exc.value.errors)


def test_decompile_roundtrip() -> None:
    yaml_doc = compile_canvas_document(_fixture("linear_three_node.json"))
    canvas = decompile_playbook_document(yaml_doc)
    roundtrip = compile_canvas_document(canvas)

    assert [step["id"] for step in roundtrip["steps"]] == ["summarize", "notify"]
    assert roundtrip["entry"] == "summarize"


def test_trigger_sets_entry() -> None:
    yaml_doc = compile_canvas_document(_fixture("linear_three_node.json"))

    assert yaml_doc["entry"] == "summarize"


def test_layout_persisted_separately(tmp_path: Path) -> None:
    store = PlaybookStudioStore(tmp_path)
    canvas = _fixture("linear_three_node.json")
    yaml_doc = compile_canvas_document(canvas)
    layout = {
        "positions": {node["id"]: node["position"] for node in canvas["nodes"]},
        "viewport": canvas["viewport"],
    }

    store.save("daily_digest", yaml_doc, layout)

    saved_yaml = (tmp_path / "daily_digest.yaml").read_text(encoding="utf-8")
    saved_layout = json.loads((tmp_path / "daily_digest.layout.json").read_text(encoding="utf-8"))
    assert "position" not in saved_yaml
    assert saved_layout["positions"]["summarize"] == {"x": 320, "y": 120}
