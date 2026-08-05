"""Studio publish flow tests."""

from __future__ import annotations

import json
import asyncio
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from keprix.api.main import app
from keprix.playbook.sdk_workflow import start_workflow_run

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "playbooks" / "canvas"


def _fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


@pytest.mark.asyncio
async def test_personal_publish_auto_publishes_without_scout(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("LABYRINTH_ENABLED", raising=False)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.put("/api/playbooks/studio/daily_digest", json={"canvas": _fixture("linear_three_node.json")})
        response = await client.post(
            "/api/playbooks/studio/daily_digest/publish",
            json={"scope": "personal", "note": "ship"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "published"
    assert len(body["version_hash"]) == 64


@pytest.mark.asyncio
async def test_scout_enabled_org_scope_pending(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("KEPRIX_EDITION", "enterprise")
    monkeypatch.setenv("LABYRINTH_ENABLED", "1")
    monkeypatch.setenv("LABYRINTH_SCOUT_WEBHOOK_URL", "https://scout.example/webhook")

    async def fake_emit(event_type, payload, *, workspace_id):
        assert event_type == "playbook_publish_requested"
        assert payload["scope"] == "org"
        return "evt_test"

    monkeypatch.setattr("keprix.playbook.studio_routes.emit_scout_lifecycle_event", fake_emit)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.put("/api/playbooks/studio/daily_digest", json={"canvas": _fixture("linear_three_node.json")})
        response = await client.post(
            "/api/playbooks/studio/daily_digest/publish",
            json={"scope": "org", "note": "org ship"},
        )

    assert response.status_code == 200
    assert response.json()["status"] == "pending_approval"
    assert response.json()["scout_event_id"] == "evt_test"


@pytest.mark.asyncio
async def test_callback_approve_publishes_status(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("KEPRIX_EDITION", "enterprise")
    monkeypatch.setenv("LABYRINTH_ENABLED", "1")
    monkeypatch.setenv("LABYRINTH_SCOUT_WEBHOOK_URL", "https://scout.example/webhook")
    monkeypatch.setenv("SCOUT_CALLBACK_SECRET", "callback-secret")
    async def fake_emit(*args, **kwargs):
        return None

    monkeypatch.setattr("keprix.playbook.studio_routes.emit_scout_lifecycle_event", fake_emit)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.put("/api/playbooks/studio/daily_digest", json={"canvas": _fixture("linear_three_node.json")})
        publish = await client.post(
            "/api/playbooks/studio/daily_digest/publish",
            json={"scope": "org"},
        )
        response = await client.post(
            "/api/scout/callbacks/playbook-publish",
            headers={"X-Scout-Callback-Secret": "callback-secret"},
            json={
                "playbook_id": "daily_digest",
                "version_hash": publish.json()["version_hash"],
                "decision": "approve",
            },
        )

    assert response.status_code == 200
    assert response.json()["status"] == "published"


@pytest.mark.asyncio
async def test_org_publish_403_in_community(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("KEPRIX_EDITION", "community")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.put("/api/playbooks/studio/daily_digest", json={"canvas": _fixture("linear_three_node.json")})
        response = await client.post(
            "/api/playbooks/studio/daily_digest/publish",
            json={"scope": "org"},
        )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_run_completion_emits_scout_telemetry(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict] = []

    async def fake_emit(event_type, payload, *, workspace_id):
        calls.append({"event_type": event_type, "payload": payload, "workspace_id": workspace_id})
        return "evt_run"

    monkeypatch.setattr("keprix.playbook.runtime.runner.emit_scout_lifecycle_event", fake_emit)
    await start_workflow_run(
        {
            "graph_id": "telemetry_playbook",
            "steps": [
                {
                    "id": "notify",
                    "type": "agent_task",
                    "config": {
                        "prompt": "notify",
                        "connector_id": "telegram",
                        "tools": ["send_telegram_message"],
                    },
                }
            ],
            "edges": [],
        },
        workspace_id="ws-telemetry",
        initial_state={"_playbook_version_hash": "abc"},
    )
    await asyncio.sleep(0)

    assert calls
    assert calls[0]["event_type"] == "playbook_run_completed"
    assert calls[0]["payload"]["playbook_id"] == "telemetry_playbook"
    assert calls[0]["payload"]["version_hash"] == "abc"
    assert calls[0]["payload"]["connector_ids_used"] == ["telegram"]
