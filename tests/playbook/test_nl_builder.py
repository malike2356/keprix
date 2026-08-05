"""Tests for NL playbook YAML generation (Prompt 208)."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from httpx import ASGITransport, AsyncClient

from keprix.api.main import app
from keprix.playbook.nl_builder import (
    PlaybookDraftRequest,
    draft_to_run_spec,
    extract_yaml_text,
    generate_playbook_yaml,
    parse_playbook_yaml,
    validate_playbook_document,
)
from keprix.evals.playbook.validators import load_eval_suite_cases, validate_draft_yaml

FIXTURE_YAML = """
id: daily-digest
name: Daily digest playbook
description: Read email and write a digest note
steps:
  - id: fetch_email
    type: agent_task
    prompt: List unread email headers
    tools: []
  - id: write_digest
    type: agent_task
    prompt: Write a digest note from {{ steps.fetch_email.output }}
    tools: []
edges:
  - from: fetch_email
    to: write_digest
""".strip()

HTTP_FIXTURE_YAML = """
id: status-poll
name: Status poll playbook
description: GET status API and branch on server errors
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
    prompt: Alert operators about API failure
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


async def _mock_llm(user_message: str, *, model_id: str | None = None) -> tuple[str, str]:
    _ = (user_message, model_id)
    if "500" in user_message or "status API" in user_message:
        return HTTP_FIXTURE_YAML, "mock:fixture"
    return FIXTURE_YAML, "mock:fixture"


def test_extract_yaml_text_strips_fence() -> None:
    raw = "```yaml\nid: demo\nsteps:\n  - id: one\n    type: agent_task\nedges: []\n```"
    text = extract_yaml_text(raw)
    assert text.startswith("id: demo")


def test_parse_and_validate_fixture_yaml() -> None:
    parsed = parse_playbook_yaml(FIXTURE_YAML)
    warnings = validate_playbook_document(parsed, FIXTURE_YAML)
    assert parsed["id"] == "daily-digest"
    assert "{{ steps.fetch_email.output }}" in FIXTURE_YAML
    assert not any("n8n" in warning for warning in warnings)


@pytest.mark.asyncio
async def test_generate_playbook_yaml_with_mock_llm() -> None:
    result = await generate_playbook_yaml(
        PlaybookDraftRequest(prompt="Read email and write a daily digest note"),
        llm_complete=_mock_llm,
    )
    assert result.playbook_id == "daily-digest"
    assert "agent_task" in result.yaml_text
    assert result.run_spec["graph_id"] == "daily-digest"
    assert len(result.run_spec["steps"]) == 2


@pytest.mark.asyncio
async def test_draft_api_returns_parseable_yaml(monkeypatch) -> None:
    async def _patched(request, *, llm_complete=None, model_id=None):
        from keprix.playbook.nl_builder import generate_playbook_yaml as original

        return await original(request, llm_complete=_mock_llm, model_id=model_id)

    monkeypatch.setattr(
        "keprix.playbook.nl_builder_routes.generate_playbook_yaml",
        _patched,
    )
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/playbooks/draft-from-prompt",
            json={"prompt": "Read email and write a daily digest note"},
        )
    assert response.status_code == 200
    payload = response.json()
    doc = yaml.safe_load(payload["yaml_text"])
    assert doc["id"] == payload["playbook_id"]
    assert any(step["type"] == "agent_task" for step in doc["steps"])


def test_eval_suite_fixtures_validate_with_mock_yaml() -> None:
    suite_path = (
        Path(__file__).resolve().parents[2] / "evals" / "suites" / "playbook" / "nl_draft_basics.yaml"
    )
    cases = load_eval_suite_cases(str(suite_path))
    assert len(cases) >= 2
    digest_case = next(case for case in cases if case["id"] == "daily_digest")
    http_case = next(case for case in cases if case["id"] == "http_poll")
    assert validate_draft_yaml(FIXTURE_YAML, digest_case) == []
    assert validate_draft_yaml(HTTP_FIXTURE_YAML, http_case) == []


def test_draft_to_run_spec_maps_agent_tasks() -> None:
    parsed = parse_playbook_yaml(FIXTURE_YAML)
    spec = draft_to_run_spec(parsed)
    assert spec["graph_id"] == "daily-digest"
    assert any(step["type"] == "agent_task" for step in spec["steps"])
