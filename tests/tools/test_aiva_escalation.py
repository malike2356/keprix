"""Tests for K05 Aiva human VA escalation."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from keprix.aiva_escalation.confidence import estimate_confidence, should_escalate
from keprix.aiva_escalation.config import EscalationConfig
from keprix.aiva_escalation.cron_seed import ESCALATION_CRON_JOBS
from keprix.aiva_escalation.service import EscalationService, reset_escalation_service_for_tests
from keprix.aiva_escalation.store import reset_escalation_store_for_tests


@pytest.fixture()
def esc(tmp_path: Path) -> EscalationService:
    store = reset_escalation_store_for_tests(tmp_path / "esc.sqlite")
    cfg = EscalationConfig(
        confidence_threshold=0.7,
        holding_message_template="Let me look into that for you. I'll be right back.",
        notify_channels=["dashboard", "telegram"],
        timeout_minutes=30,
        telegram_chat_id="12345",
    )
    return reset_escalation_service_for_tests(store, cfg)


def test_confidence_heuristic_uncertain_is_low() -> None:
    score = estimate_confidence(assistant_text="I'm not sure I can answer that.")
    assert score < 0.7
    assert should_escalate(score, 0.7) is True


def test_confidence_explicit_overrides() -> None:
    score = estimate_confidence(assistant_text="Definitely yes.", explicit=0.4)
    assert score == 0.4


@pytest.mark.parametrize(
    "assistant_text",
    [
        "Hi. How can I help?",
        "Hello. What would you like to work on?",
        "Which campaign do you mean?",
    ],
)
def test_normal_short_questions_do_not_trigger_escalation(assistant_text: str) -> None:
    score = estimate_confidence(assistant_text=assistant_text)
    assert score >= 0.7
    assert should_escalate(score, 0.7) is False


def test_escalate_when_below_threshold(esc: EscalationService) -> None:
    result = esc.maybe_escalate_turn(
        workspace_id="ws_1",
        worker_id="worker_a",
        session_id="sess_1",
        messages=[{"role": "user", "content": "What is our refund policy for enterprise?"}],
        assistant_text="I'm not sure about the enterprise refund policy.",
    )
    assert result is not None
    assert result["escalated"] is True
    assert "I'll be right back" in result["holding_message"] or "look into" in result["holding_message"].lower()
    assert result["escalation"]["status"] == "pending"
    assert result["notify"]
    assert any(n.get("channel") == "dashboard" for n in result["notify"])


def test_holding_message_on_create(esc: EscalationService) -> None:
    created = esc.create(
        workspace_id="ws_1",
        worker_id="w1",
        original_input="Help with billing",
        confidence_score=0.3,
    )
    assert created["holding_message"]
    assert created["escalation"]["holding_message"] == created["holding_message"]


def test_assign_complete_flows_response(esc: EscalationService) -> None:
    created = esc.create(
        workspace_id="ws_1",
        worker_id="w1",
        original_input="Need a quote",
        confidence_score=0.2,
    )
    eid = created["escalation"]["id"]
    assigned = esc.assign(eid, "va_jane")
    assert assigned["status"] == "assigned"
    assert assigned["assigned_va"] == "va_jane"

    done = esc.complete(eid, "Enterprise plan is £99/mo.", assigned_va="va_jane")
    assert done["status"] == "completed"
    assert done["va_response"] == "Enterprise plan is £99/mo."
    assert done["completed_at"]
    assert any(a.get("event") == "completed" for a in (done.get("audit_log") or []))


def test_queue_visible(esc: EscalationService) -> None:
    esc.create(workspace_id="ws_1", worker_id="w1", original_input="A", confidence_score=0.1)
    esc.create(workspace_id="ws_1", worker_id="w1", original_input="B", confidence_score=0.1)
    queue = esc.get_queue("ws_1", status="pending")
    assert queue["count"] == 2


def test_timeout_auto_reassigns(esc: EscalationService) -> None:
    created = esc.create(
        workspace_id="ws_1",
        worker_id="w1",
        original_input="stale",
        confidence_score=0.1,
    )
    eid = created["escalation"]["id"]
    esc.assign(eid, "va_old")
    # Backdate created_at
    old = (datetime.now(timezone.utc) - timedelta(minutes=60)).replace(microsecond=0).isoformat()
    with esc.store._lock:
        esc.store._conn.execute(
            "UPDATE aiva_escalations SET created_at = ?, reassigned_at = NULL WHERE id = ?",
            (old, eid),
        )
        esc.store._conn.commit()

    result = esc.process_timeouts(timeout_minutes=30)
    assert result["reassigned"] >= 1
    row = esc.store.get_escalation(eid)
    assert row is not None
    assert row["status"] == "pending"
    assert row["assigned_va"] is None
    assert any(a.get("event") == "timeout_reassigned" for a in (row.get("audit_log") or []))


def test_human_assist_request(esc: EscalationService) -> None:
    result = esc.human_assist_request(
        workspace_id="ws_1",
        worker_id="w1",
        reason="User asked for a human",
        urgency="urgent",
        details="Billing dispute",
    )
    assert result["assist_request"]["urgency"] == "urgent"
    assert result["escalation"]["escalation_type"] == "manual_request"


def test_tools_and_cron(tmp_path: Path) -> None:
    store = reset_escalation_store_for_tests(tmp_path / "tools.sqlite")
    reset_escalation_service_for_tests(store, EscalationConfig(notify_channels=["dashboard"]))
    import tools.escalation_tools as escalation_tools  # noqa: F401
    from tools.registry import registry

    assert registry.get_entry("escalation_create") is not None
    raw = registry.dispatch(
        "escalation_create",
        {
            "workspace_id": "ws_t",
            "worker_id": "w1",
            "original_input": "Need help",
            "confidence_score": 0.2,
        },
    )
    data = json.loads(raw)
    assert data["escalation"]["status"] == "pending"

    queue = json.loads(
        registry.dispatch("escalation_get_queue", {"workspace_id": "ws_t", "status": "pending"})
    )
    assert queue["count"] >= 1

    names = {j["name"] for j in ESCALATION_CRON_JOBS}
    assert "aiva-escalation-timeout" in names


@pytest.mark.asyncio
async def test_bridge_returns_holding_on_low_confidence(tmp_path: Path) -> None:
    from keprix.agent.carina_bridge import CarinaAgentBridge, LlmTurn, ProviderPool, SessionStore

    store = reset_escalation_store_for_tests(tmp_path / "bridge.sqlite")
    reset_escalation_service_for_tests(
        store,
        EscalationConfig(confidence_threshold=0.7, notify_channels=["dashboard"]),
    )

    async def fake_complete(**kwargs):  # type: ignore[no-untyped-def]
        return LlmTurn(
            content="I'm not sure I can help with that.",
            tool_calls=[],
            finish_reason="stop",
            usage={"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
        )

    bridge = CarinaAgentBridge(
        provider_pool=ProviderPool(complete_fn=fake_complete, fallbacks=[]),
        session_store=SessionStore(),
        max_iterations=3,
        timeout_seconds=30,
    )
    result = await bridge.run(
        workspace_id="ws_1",
        session_id="s1",
        model="test",
        temperature=0,
        system_prompt="You are Aiva.",
        messages=[{"role": "user", "content": "Complex legal question"}],
        tools=[],
        carina_tools=[],
        worker_id="worker_a",
        inject_worker_kb=False,
        escalation_enabled=True,
    )
    assert result["finish_reason"] == "escalated"
    assert "look into" in result["message"]["content"].lower() or "right back" in result["message"]["content"].lower()
    assert result["escalation"]["id"]
