"""Prompt 24 notification system tests."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from httpx import ASGITransport, AsyncClient

from keprix.api.main import app
from keprix.backend.notifications.channels import get_channel_delivery
from keprix.backend.notifications.delivery import get_delivery_service
from keprix.backend.notifications.digest import get_digest_service
from keprix.backend.notifications.escalation import get_escalation_service
from keprix.backend.notifications.inbox import get_inbox_service
from keprix.backend.notifications.preferences import get_preferences_service
from keprix.backend.notifications.store import reset_notification_store


@pytest.fixture
def notifications_env(tmp_path, monkeypatch):
    monkeypatch.setenv("KEPRIX_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("AUTH_ENABLED", "false")
    reset_notification_store()
    import keprix.backend.notifications.channels as channels_module
    import keprix.backend.notifications.delivery as delivery_module
    import keprix.backend.notifications.digest as digest_module
    import keprix.backend.notifications.escalation as escalation_module
    import keprix.backend.notifications.inbox as inbox_module
    import keprix.backend.notifications.preferences as preferences_module

    channels_module._delivery = None
    delivery_module._service = None
    digest_module._service = None
    escalation_module._service = None
    inbox_module._service = None
    preferences_module._service = None
    get_channel_delivery().reset_group_deliveries()
    return tmp_path


@pytest.mark.asyncio
async def test_notification_appears_in_unified_inbox(notifications_env) -> None:
    await get_inbox_service().send_notification(
        "ws-1",
        "job_complete",
        severity="info",
        title="Job done",
        message="Export finished successfully.",
        href="/jobs/1",
    )
    rows = get_inbox_service().list_inbox("ws-1")
    assert len(rows) == 1
    assert rows[0]["notification_type"] == "job_complete"
    assert rows[0]["read"] is False


@pytest.mark.asyncio
async def test_sensitive_notification_not_sent_to_group_chat(notifications_env) -> None:
    prefs = get_preferences_service().get("ws-1", "default")
    prefs["channels_enabled"]["slack"] = True
    get_preferences_service().update("ws-1", "default", {"channels_enabled": prefs["channels_enabled"]})

    delivery = get_channel_delivery()
    delivery.reset_group_deliveries()
    notification = await get_inbox_service().send_notification(
        "ws-1",
        "security_alert",
        severity="critical",
        title="Credential leak",
        message="API key exposed in logs.",
        sensitive=True,
    )
    group_posts = delivery.pop_group_deliveries()
    assert group_posts == []
    blocked = [row for row in notification["deliveries"] if row.get("status") == "blocked"]
    assert blocked or "slack" not in [row.get("channel") for row in notification["deliveries"]]


@pytest.mark.asyncio
async def test_quiet_hours_delay_non_critical(notifications_env) -> None:
    get_preferences_service().update(
        "ws-1",
        "default",
        {
            "quiet_hours_enabled": True,
            "quiet_hours_start": "00:00",
            "quiet_hours_end": "23:59",
            "digest_enabled": True,
        },
    )
    notification = await get_inbox_service().send_notification(
        "ws-1",
        "job_complete",
        severity="info",
        title="Job done",
        message="Finished.",
    )
    assert notification["delayed_for_digest"] is True
    queue = get_inbox_service()._store.list_digest_queue("ws-1")
    assert len(queue) == 1


@pytest.mark.asyncio
async def test_critical_bypasses_quiet_hours(notifications_env) -> None:
    get_preferences_service().update(
        "ws-1",
        "default",
        {
            "quiet_hours_enabled": True,
            "quiet_hours_start": "00:00",
            "quiet_hours_end": "23:59",
        },
    )
    notification = await get_inbox_service().send_notification(
        "ws-1",
        "security_alert",
        severity="critical",
        title="Intrusion detected",
        message="Lock account immediately.",
    )
    assert notification["delayed_for_digest"] is False
    assert notification["deliveries"]


@pytest.mark.asyncio
async def test_approval_reminder_escalates_after_timeout(notifications_env) -> None:
    get_preferences_service().update("ws-1", "default", {"escalation_delay_minutes": 5})
    notification = await get_inbox_service().send_notification(
        "ws-1",
        "approval_needed",
        severity="warning",
        title="Approve deployment",
        message="Release waiting for sign-off.",
        href="/approvals/1",
    )
    escalations = get_inbox_service()._store.list_escalations("ws-1", status="pending")
    assert len(escalations) == 1
    escalation = escalations[0]
    get_inbox_service()._store.update_escalation(
        "ws-1",
        str(escalation["id"]),
        {"escalate_at": (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()},
    )
    processed = await get_escalation_service().process_due_escalations("ws-1")
    assert len(processed) == 1
    rows = get_inbox_service().list_inbox("ws-1")
    assert len(rows) >= 2


@pytest.mark.asyncio
async def test_delivery_failure_retries(notifications_env) -> None:
    get_preferences_service().update(
        "ws-1",
        "default",
        {"channels_enabled": {"in_app": True, "email": False, "push": True}},
    )
    notification = await get_inbox_service().send_notification(
        "ws-1",
        "billing_failed",
        severity="critical",
        title="Payment failed",
        message="Update billing details.",
        simulate_delivery_failure=True,
    )
    failed = [row for row in notification["deliveries"] if row.get("status") == "failed"]
    assert failed
    retries = await get_delivery_service().retry_failed_deliveries("ws-1")
    assert retries
    assert any(row.get("status") == "delivered" for row in retries)


@pytest.mark.asyncio
async def test_user_preference_suppresses_channel(notifications_env) -> None:
    get_preferences_service().update(
        "ws-1",
        "default",
        {"channels_enabled": {"in_app": True, "email": False, "push": False}},
    )
    notification = await get_inbox_service().send_notification(
        "ws-1",
        "usage_limit_warning",
        severity="warning",
        title="Usage high",
        message="You are at 90% capacity.",
    )
    channels = [row.get("channel") for row in notification["deliveries"]]
    assert "email" not in channels
    assert "in_app" in channels


@pytest.mark.asyncio
async def test_inbox_api_lists_notifications(notifications_env) -> None:
    await get_inbox_service().send_notification(
        "default",
        "research_complete",
        severity="info",
        title="Research done",
        message="Playbook finished.",
    )
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/notifications/inbox?workspace_id=default")
    assert response.status_code == 200
    body = response.json()
    assert body["count"] >= 1
    assert body["unread_count"] >= 1


@pytest.mark.asyncio
async def test_digest_flush_after_quiet_hours(notifications_env) -> None:
    get_preferences_service().update(
        "ws-1",
        "default",
        {"quiet_hours_enabled": False, "digest_email": "ops@example.com"},
    )
    get_inbox_service()._store.queue_digest(
        "ws-1",
        {"title": "Queued", "message": "Delayed alert"},
    )
    result = await get_digest_service().flush_digest_queue("ws-1")
    assert result["flushed"] == 1
