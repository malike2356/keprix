"""Agent runtime bridge tests with mocked LLM."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from keprix.agent_apps.agent_runtime import (
    AgentAppEnvError,
    AgentAppPermissionError,
    build_system_prompt,
    build_user_message,
    readiness_state,
    run_agent_app_llm,
    run_agent_app_llm_sync,
)
from keprix.agent_apps.app_manifest import load_manifest
from keprix.agent_apps.catalog import template_dir
from keprix.agent_apps.lifecycle import LifecycleEvent
from keprix.agent_apps.registry import AgentAppRegistry, sample_app_dir
from keprix.agent_apps.runner_core import run_agent_app
from keprix.public_api.agent_runtime import AgentChatResult


@pytest.fixture()
def mock_chat_completion(monkeypatch: pytest.MonkeyPatch) -> AsyncMock:
    async def _fake(**_kwargs):
        return AgentChatResult(
            final_response="Standup: shipped agent apps bridge.",
            session_id="agent-app:test",
            prompt_tokens=3,
            completion_tokens=5,
            total_tokens=8,
        )

    mock = AsyncMock(side_effect=_fake)
    monkeypatch.setattr("keprix.public_api.agent_runtime.run_agent_chat_completion", mock)
    return mock


def test_readiness_reports_missing_env(monkeypatch: pytest.MonkeyPatch) -> None:
    source = template_dir("daily-standup")
    assert source is not None
    manifest = load_manifest(source)
    monkeypatch.setattr(
        "keprix.agent_apps.agent_runtime.resolve_env_value",
        lambda _key: None,
    )
    state = readiness_state(manifest)
    assert state["ready"] is False
    assert "KEPRIX_DEFAULT_PROVIDER" in state["missing_env"]


def test_readiness_reports_missing_email_permission(monkeypatch: pytest.MonkeyPatch) -> None:
    app_dir = sample_app_dir().parent / ".." / "catalog" / "daily-standup"
    app_dir = template_dir("daily-standup")
    assert app_dir is not None
    manifest = load_manifest(app_dir)
    monkeypatch.setenv("KEPRIX_DEFAULT_PROVIDER", "deepseek")
    manifest.required_permissions = ["email_read"]
    state = readiness_state(manifest)
    assert "email_read" in state["missing_permissions"]


@pytest.mark.asyncio
async def test_run_agent_app_llm_mocked(
    mock_chat_completion: AsyncMock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("KEPRIX_DEFAULT_PROVIDER", "deepseek")
    source = template_dir("daily-standup")
    assert source is not None
    manifest = load_manifest(source)
    result = await run_agent_app_llm(
        source,
        manifest,
        inputs={"focus": "agent apps"},
    )
    assert "Standup" in result.output
    mock_chat_completion.assert_awaited_once()
    kwargs = mock_chat_completion.await_args.kwargs
    assert kwargs["messages"][0]["role"] == "system"
    assert "standup assistant" in kwargs["messages"][0]["content"].lower()
    assert kwargs["messages"][1]["content"]


def test_run_agent_app_llm_sync_wrapper(mock_chat_completion: AsyncMock, monkeypatch: pytest.MonkeyPatch) -> None:
    source = template_dir("daily-standup")
    assert source is not None
    manifest = load_manifest(source)
    monkeypatch.setenv("KEPRIX_DEFAULT_PROVIDER", "deepseek")
    result = run_agent_app_llm_sync(
        source,
        manifest,
        input_text="",
        context={"form": {"focus": "sync path"}},
    )
    assert result["status"] == "ok"
    assert "Standup" in result["output"]


def test_build_user_message_uses_prompt_template() -> None:
    source = template_dir("daily-standup")
    assert source is not None
    manifest = load_manifest(source)
    message = build_user_message(manifest, input_text="", context={"form": {"focus": "billing"}})
    assert "billing" in message


def test_build_system_prompt_includes_tools() -> None:
    source = template_dir("daily-standup")
    assert source is not None
    manifest = load_manifest(source)
    prompt = build_system_prompt(source, manifest)
    assert "tasks" in prompt


def test_python_runtime_unchanged(tmp_path: Path) -> None:
    registry = AgentAppRegistry(base_dir=tmp_path / "registry")
    registry.install(sample_app_dir())
    app_dir = registry.app_dir("hello-agent")
    assert app_dir is not None
    result = run_agent_app(app_dir, input_text="Ada", context={"form": {"name": "Ada"}})
    assert "Ada" in result["result"]["output"]
    events = [item["event"] for item in result["traces"]]
    assert LifecycleEvent.BEFORE_RUN.value in events
    assert LifecycleEvent.AFTER_RUN.value in events


def test_permission_error_emits_approval_event(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source = template_dir("daily-standup")
    assert source is not None
    registry = AgentAppRegistry(base_dir=tmp_path / "registry")
    registry.install(source)
    app_dir = registry.app_dir("daily-standup")
    assert app_dir is not None
    monkeypatch.setenv("KEPRIX_DEFAULT_PROVIDER", "deepseek")
    (app_dir / "agent.yaml").write_text(
        (app_dir / "agent.yaml").read_text(encoding="utf-8").replace(
            "required_permissions:\n  - network",
            "required_permissions:\n  - email_read",
        ),
        encoding="utf-8",
    )

    with pytest.raises(AgentAppPermissionError):
        run_agent_app(app_dir, input_text="hello", context={})

    from keprix.agent_apps.lifecycle import get_run_traces

    traces = get_run_traces("daily-standup")
    assert any(item.get("event") == LifecycleEvent.ON_APPROVAL_REQUESTED.value for item in traces)


def test_missing_env_raises_actionable_error(monkeypatch: pytest.MonkeyPatch) -> None:
    source = template_dir("daily-standup")
    assert source is not None
    manifest = load_manifest(source)
    monkeypatch.setattr(
        "keprix.agent_apps.agent_runtime.resolve_env_value",
        lambda _key: None,
    )
    with pytest.raises(AgentAppEnvError):
        run_agent_app_llm_sync(source, manifest, input_text="hello", context={})
