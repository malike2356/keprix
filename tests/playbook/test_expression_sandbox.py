"""Tests for playbook expression sandbox (Prompt 211)."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from keprix.playbook.expression_sandbox import (
    ExpressionError,
    build_expression_context,
    evaluate_condition,
    render_template,
    resolve_path,
)
from keprix.playbook.nl_builder import parse_playbook_yaml
from keprix.playbook.runtime import END, PlaybookRunner, RunStatus
from keprix.playbook.sdk_workflow import compile_workflow_spec
from keprix.playbook.yaml_compiler import compile_playbook_document

HTTP_FIXTURE_YAML = """
id: status-poll
name: Status poll playbook
steps:
  - id: fetch_status
    type: http
    url: https://example.com/status
    method: GET
  - id: check_error
    type: condition
    expression: "steps.fetch_status.output.status_code >= 500"
    on_true: alert_ops
    on_false: log_ok
  - id: alert_ops
    type: agent_task
    prompt: Alert operators
    tools: []
  - id: log_ok
    type: agent_task
    prompt: Log healthy status
    tools: []
edges:
  - from: fetch_status
    to: check_error
  - from: check_error
    to: alert_ops
  - from: check_error
    to: log_ok
""".strip()


@pytest.fixture
def sample_context() -> dict:
    return build_expression_context(
        {
            "fetch_status_output": {"status_code": 503, "body": "error"},
            "triage_output": {"urgency": "high"},
            "region": "eu",
        }
    )


def test_allowed_condition_expressions(sample_context) -> None:
    assert evaluate_condition("steps.fetch_status.output.status_code >= 500", sample_context)
    assert evaluate_condition("steps.triage.output.urgency == 'high'", sample_context)
    assert evaluate_condition("state.region == 'eu'", sample_context)
    assert evaluate_condition("true", sample_context)
    assert not evaluate_condition("false", sample_context)


def test_rejects_injection_attempts() -> None:
    with pytest.raises(ExpressionError):
        evaluate_condition("__import__('os').system('rm -rf /')", {})
    with pytest.raises(ExpressionError):
        evaluate_condition("open('/etc/passwd')", {})
    with pytest.raises(ExpressionError):
        evaluate_condition("().__class__.__bases__[0].__subclasses__()", {})
    with pytest.raises(ExpressionError):
        evaluate_condition("len(steps.fetch_status.output.status_code)", {})


def test_render_template_nested_paths(sample_context) -> None:
    rendered = render_template(
        "Status={{ steps.fetch_status.output.status_code }} region={{ state.region }}",
        sample_context,
    )
    assert rendered == "Status=503 region=eu"


def test_render_template_unknown_token_becomes_empty(sample_context, caplog) -> None:
    rendered = render_template("Hello {{ steps.missing.output.name }}", sample_context)
    assert rendered == "Hello "
    assert any("missing" in record.message for record in caplog.records)


def test_resolve_path_steps_and_state(sample_context) -> None:
    assert resolve_path("steps.fetch_status.output.status_code", sample_context) == 503
    assert resolve_path("state.region", sample_context) == "eu"


@pytest.mark.asyncio
async def test_condition_step_routes_on_true_branch(monkeypatch) -> None:
    async def _mock_http(**kwargs):
        return {"status_code": 503, "body": "error"}

    monkeypatch.setattr("keprix.playbook.sdk_workflow._execute_http_step", _mock_http)
    parsed = parse_playbook_yaml(HTTP_FIXTURE_YAML)
    graph = compile_playbook_document(parsed).compile()
    runner = PlaybookRunner(graph)
    run = await runner.start(workspace_id="test")
    assert run.status == RunStatus.COMPLETED
    assert "Alert operators" in str(run.state.get("alert_ops_output", {}))


@pytest.mark.asyncio
async def test_condition_step_routes_on_false_branch(monkeypatch) -> None:
    async def _mock_http(**kwargs):
        return {"status_code": 200, "body": "ok"}

    monkeypatch.setattr("keprix.playbook.sdk_workflow._execute_http_step", _mock_http)
    parsed = parse_playbook_yaml(HTTP_FIXTURE_YAML)
    graph = compile_playbook_document(parsed).compile()
    runner = PlaybookRunner(graph)
    run = await runner.start(workspace_id="test")
    assert run.status == RunStatus.COMPLETED
    assert "Log healthy status" in str(run.state.get("log_ok_output", {}))


@pytest.mark.asyncio
async def test_invalid_expression_fails_step() -> None:
    spec = {
        "graph_id": "bad-condition",
        "steps": [
            {
                "id": "gate",
                "type": "condition",
                "config": {"expression": "__import__('os')"},
            }
        ],
        "edges": [{"from": "gate", "to": END}],
    }
    graph = compile_workflow_spec(spec).compile()
    runner = PlaybookRunner(graph)
    run = await runner.start(workspace_id="test")
    assert run.status == RunStatus.FAILED
    assert run.error is not None
    assert "invalid_expression" in run.error


@pytest.mark.asyncio
async def test_agent_task_prompt_template_rendering() -> None:
    spec = {
        "graph_id": "prompt-template",
        "steps": [
            {
                "id": "fetch_email",
                "type": "task",
                "config": {"key": "fetch_email_output", "value": {"subject": "Weekly"}},
            },
            {
                "id": "write_digest",
                "type": "agent_task",
                "config": {"prompt": "Digest for {{ steps.fetch_email.output.subject }}"},
            },
        ],
        "edges": [{"from": "fetch_email", "to": "write_digest"}, {"from": "write_digest", "to": END}],
    }
    graph = compile_workflow_spec(spec).compile()
    runner = PlaybookRunner(graph)
    run = await runner.start(workspace_id="test")
    prompt = run.state["write_digest_output"]["prompt"]
    assert prompt == "Digest for Weekly"


def test_playbook_package_has_no_bare_eval_on_user_strings() -> None:
    playbook_dir = Path(__file__).resolve().parents[2] / "src" / "keprix" / "playbook"
    offenders: list[str] = []
    for path in playbook_dir.rglob("*.py"):
        if path.name == "expression_sandbox.py":
            continue
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "eval":
                offenders.append(f"{path.relative_to(playbook_dir)}:{node.lineno}")
    assert offenders == []
