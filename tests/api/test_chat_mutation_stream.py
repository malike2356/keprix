"""API tests for chat mutation streaming (Prompt 139)."""

from __future__ import annotations

import json
from dataclasses import asdict
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from keprix.agent.keprix.mutation import MutationEngine
from keprix.agent.keprix.store import GeneratedToolStore
from keprix.api.server import create_app
from keprix.auth.session import AuthManager
from keprix.governance.policy_receiver import get_policy_registry
from keprix.security.rate_limiter import reset_rate_limits
from keprix.workspace.repository import WorkspaceRepository


@pytest.fixture
def mutation_chat_client(tmp_path, monkeypatch):
    tools_dir = tmp_path / "generated" / "tools"
    skills_dir = tmp_path / "generated" / "skills"
    store_dir = tmp_path / "mutation"
    tools_dir.mkdir(parents=True)
    skills_dir.mkdir(parents=True)

    monkeypatch.setenv("KEPRIX_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("KEPRIX_ADMIN_PASSWORD", "admin-pass")
    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setenv("KEPRIX_MUTATION_ENABLED", "true")
    monkeypatch.setenv("KEPRIX_MUTATION_STREAM_WAIT_APPROVAL", "false")
    monkeypatch.setenv("KEPRIX_GENERATED_TOOLS_DIR", str(tools_dir))
    monkeypatch.setenv("KEPRIX_GENERATED_SKILLS_DIR", str(skills_dir))
    monkeypatch.setenv("KEPRIX_MUTATION_REQUIRED_CHANNELS", "web_ui")
    monkeypatch.setenv("KEPRIX_TOOL_SIGNING_KEY", str(tmp_path / "signing.pem"))
    monkeypatch.setenv("KEPRIX_TOOL_VERIFY_KEY", str(tmp_path / "verify.pem"))
    reset_rate_limits()
    get_policy_registry().reload_from_store([])

    store = GeneratedToolStore(path=store_dir / "generated_tools.json")
    monkeypatch.setattr("keprix.agent.keprix.store.get_generated_tool_store", lambda: store)
    monkeypatch.setattr("keprix.agent.keprix.mutation.get_generated_tool_store", lambda: store)
    monkeypatch.setattr("keprix.agent.keprix.approval.get_generated_tool_store", lambda: store)
    monkeypatch.setattr("keprix.agent.keprix.auditor.get_generated_tool_store", lambda: store)
    monkeypatch.setattr("keprix.agent.keprix.mutation._engine", None)

    monkeypatch.setattr("keprix.database.get_session_factory", lambda: None)
    monkeypatch.setattr("keprix.observability.metrics.get_session_factory", lambda: None)

    auth = AuthManager(str(tmp_path / "auth.json"))
    monkeypatch.setattr("keprix.auth.routes.auth_manager", auth)
    monkeypatch.setattr("keprix.auth.dependencies.auth_manager", auth)

    repo = WorkspaceRepository()
    monkeypatch.setattr("keprix.workspace.repository.workspace_repo", repo)
    monkeypatch.setattr("keprix.api.conversation_routes.workspace_repo", repo)

    client = TestClient(create_app())
    login = client.post("/api/auth/login", json={"username": "admin", "password": "admin-pass"})
    token = login.json()["token"]
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client, repo, store


def _collect_stream_events(client: TestClient, session_id: str, content: str) -> list[dict]:
    events: list[dict] = []
    with client.stream(
        "POST",
        f"/api/conversations/{session_id}/messages",
        json={"content": content, "file_ids": [], "model": "ollama:llama3.2"},
    ) as response:
        assert response.status_code == 200
        for line in response.iter_lines():
            if not line:
                continue
            events.append(json.loads(line))
    return events


@pytest.mark.asyncio
async def test_chat_message_streams_mutation_event(mutation_chat_client, monkeypatch):
    client, _repo, store = mutation_chat_client
    session_id = client.post("/api/conversations", json={"title": "Mutation chat"}).json()["id"]

    run_calls: list[dict] = []

    async def fake_run_cycle(task, available_tools, *, session_id=None, trigger="gap", requested_tool=None):
        run_calls.append({"task": task, "tools": available_tools, "session_id": session_id, "trigger": trigger})
        record = store.create(
            task_that_triggered=task,
            tool_name="fetch_stock_price",
            tool_code='"""Generated tool"""\nprint("ok")',
            skill_yaml="name: fetch_stock_price",
            description="Fetch stock price",
            gap_description="No tool exists to fetch live stock prices.",
            static_analysis={"safe": True, "violations": []},
            sandbox_result={"passed": True, "output": '{"result": "ok"}', "stderr": "", "exit_code": 0},
            session_id=session_id,
            metadata={"original_task": task, "session_id": session_id},
        )
        return {
            "started": True,
            "status": "pending_approval",
            "record_id": record.id,
            "tool_name": record.tool_name,
            "sandbox_passed": True,
            "record": asdict(record),
        }

    monkeypatch.setattr(
        "keprix.agent.keprix.mutation_hook.get_mutation_engine",
        lambda: SimpleNamespace(
            detect_gap_async=MutationEngine().detect_gap_async,
            run_cycle=fake_run_cycle,
        ),
    )
    monkeypatch.setattr(
        "keprix.agent.keprix.mutation_hook.list_runtime_tool_names",
        lambda: ["todo", "web_search"],
    )

    events = _collect_stream_events(client, session_id, "fetch AAPL stock price")

    mutation_events = [event for event in events if event.get("event") == "mutation"]
    assert len(mutation_events) == 1
    mutation = mutation_events[0]
    assert mutation["toolName"] == "fetch_stock_price"
    assert mutation["id"]
    assert mutation["code"]
    assert mutation["status"] == "pending"
    assert run_calls
    assert run_calls[0]["session_id"] == session_id

    session = client.get(f"/api/conversations/{session_id}").json()
    assistant = session["messages"][-1]
    assert assistant["role"] == "assistant"
    mutation_blocks = [block for block in assistant["content"] if block.get("type") == "mutation"]
    assert len(mutation_blocks) == 1
    assert mutation_blocks[0]["toolName"] == "fetch_stock_price"


@pytest.mark.asyncio
async def test_chat_message_streams_track_time_mutation(mutation_chat_client, monkeypatch):
    client, _repo, store = mutation_chat_client
    session_id = client.post("/api/conversations", json={"title": "Time tracking"}).json()["id"]

    async def fake_run_cycle(task, available_tools, *, session_id=None, trigger="gap", requested_tool=None):
        record = store.create(
            task_that_triggered=task,
            tool_name="track_time",
            tool_code='"""Generated tool"""\nprint("ok")',
            skill_yaml="name: track_time",
            description="Track project time",
            gap_description="No tool exists to track time on projects.",
            static_analysis={"safe": True, "violations": []},
            sandbox_result={"passed": True, "output": '{"result": "ok"}', "stderr": "", "exit_code": 0},
            session_id=session_id,
        )
        return {
            "started": True,
            "status": "pending_approval",
            "record_id": record.id,
            "tool_name": record.tool_name,
            "sandbox_passed": True,
            "record": asdict(record),
        }

    monkeypatch.setattr(
        "keprix.agent.keprix.mutation_hook.get_mutation_engine",
        lambda: SimpleNamespace(
            detect_gap_async=MutationEngine().detect_gap_async,
            run_cycle=fake_run_cycle,
        ),
    )
    monkeypatch.setattr(
        "keprix.agent.keprix.mutation_hook.list_runtime_tool_names",
        lambda: ["todo", "web_search"],
    )

    events = _collect_stream_events(client, session_id, "Track my time on this project")
    mutation_events = [event for event in events if event.get("event") == "mutation"]
    assert len(mutation_events) == 1
    assert mutation_events[0]["toolName"] == "track_time"


def test_chat_mutation_disabled_falls_back_to_llm(mutation_chat_client, monkeypatch):
    client, _repo, _store = mutation_chat_client
    session_id = client.post("/api/conversations", json={"title": "Disabled"}).json()["id"]
    monkeypatch.setenv("KEPRIX_MUTATION_ENABLED", "false")

    from keprix.agent.keprix.config import get_mutation_config

    if hasattr(get_mutation_config, "cache_clear"):
        get_mutation_config.cache_clear()

    seen: dict[str, bool] = {}

    async def fake_stream_chat_completion(**kwargs):
        seen["stream_called"] = True
        yield "plain "
        yield "reply"

    monkeypatch.setattr(
        "keprix.api.chat_inference.stream_chat_completion",
        fake_stream_chat_completion,
    )

    events = _collect_stream_events(client, session_id, "fetch AAPL stock price")
    assert seen.get("stream_called") is True
    assert not any(event.get("event") == "mutation" for event in events)


def test_non_gap_message_does_not_run_cycle(mutation_chat_client, monkeypatch):
    client, _repo, _store = mutation_chat_client
    session_id = client.post("/api/conversations", json={"title": "No gap"}).json()["id"]

    run_calls: list[str] = []

    async def fake_run_cycle(task, available_tools, *, session_id=None, trigger="gap", requested_tool=None):
        run_calls.append(task)
        return {"started": False}

    async def fake_stream_chat_completion(**_kwargs):
        yield "hello"

    monkeypatch.setattr(
        "keprix.agent.keprix.mutation_hook.get_mutation_engine",
        lambda: SimpleNamespace(
            detect_gap_async=MutationEngine().detect_gap_async,
            run_cycle=fake_run_cycle,
        ),
    )
    monkeypatch.setattr(
        "keprix.api.chat_inference.stream_chat_completion",
        fake_stream_chat_completion,
    )

    events = _collect_stream_events(client, session_id, "Summarise what Keprix can do in this workspace")
    assert run_calls == []
    assert not any(event.get("event") == "mutation" for event in events)
    assert any(event.get("event") == "text_delta" for event in events)
