"""Workflow coach rule tests."""

from __future__ import annotations

from keprix.playbook.workflow_coach import suggest_next_nodes


def test_agent_task_suggests_multiple_successors() -> None:
    suggestions = suggest_next_nodes(selected_node_type="agent_task", canvas={})

    assert len(suggestions) >= 2
    assert {item.node_type for item in suggestions} >= {"condition", "http"}


def test_condition_suggests_branch_nodes() -> None:
    suggestions = suggest_next_nodes(selected_node_type="condition", canvas={})

    assert any(item.node_type == "agent_task" for item in suggestions)
    assert any(item.node_type == "human_approval" for item in suggestions)


def test_parallel_and_artifact_canvas_compile() -> None:
    from keprix.playbook.canvas_compiler import compile_canvas_document
    from keprix.playbook.yaml_compiler import compile_playbook_document

    canvas = {
        "schema_version": 1,
        "id": "artifact_demo",
        "name": "Artifact demo",
        "nodes": [
            {"id": "trigger", "type": "trigger", "position": {"x": 0, "y": 0}, "data": {"label": "Trigger"}},
            {"id": "fanout", "type": "parallel", "position": {"x": 240, "y": 0}, "data": {"label": "Fanout", "tasks": [{"id": "a", "set": {"a": True}}]}},
            {"id": "export", "type": "artifact", "position": {"x": 480, "y": 0}, "data": {"label": "Export", "name": "result", "content": "done"}},
        ],
        "edges": [
            {"id": "e_trigger_fanout", "source": "trigger", "target": "fanout", "data": {"when": None}},
            {"id": "e_fanout_export", "source": "fanout", "target": "export", "data": {"when": None}},
        ],
    }
    yaml_doc = compile_canvas_document(canvas)

    assert [step["type"] for step in yaml_doc["steps"]] == ["parallel", "artifact"]
    assert compile_playbook_document(yaml_doc).graph_id == "artifact_demo"
