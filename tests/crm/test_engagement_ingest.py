"""Engagement ingest tests (prompt 443)."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture()
def crm(tmp_path: Path):
    from keprix.crm.store import CrmStore

    return CrmStore(tmp_path / "crm.db")


def test_classify_activity_stage_unsubscribe(crm) -> None:
    ws = "ws443"
    lead = crm.create_lead(ws, name="Dana", email="dana@example.com", stage="enrolled")
    from keprix.crm.engagement import ingest_engagement

    result = ingest_engagement(
        workspace_id=ws,
        engagement_type="interested",
        body="Sounds good, tell me more",
        subject="Re: intro",
        from_address="dana@example.com",
        confidence=0.95,
        method="test",
        crm_store=crm,
        outreach_store=None,
    )
    # Resolve by email
    assert result["entity_id"] == lead["id"]
    assert result["activity"] is not None
    updated = crm.get_lead(ws, lead["id"])
    assert updated["stage"] in {"engaged", "enrolled", "contacted"}  # may Soft Wall if skip

    unsub = ingest_engagement(
        workspace_id=ws,
        engagement_type="unsubscribe",
        body="Please unsubscribe me",
        from_address="dana@example.com",
        confidence=0.99,
        crm_store=crm,
    )
    assert unsub["suppression"] is not None
    assert crm.is_suppressed(ws, channel="email", address="dana@example.com")
    assert crm.get_lead(ws, lead["id"])["stage"] in {"suppressed", "do_not_contact"}


def test_ooo_does_not_promote(crm) -> None:
    ws = "ws443b"
    lead = crm.create_lead(ws, name="Eve", email="eve@example.com", stage="contacted")
    from keprix.crm.engagement import ingest_engagement

    ingest_engagement(
        workspace_id=ws,
        engagement_type="ooo",
        body="I am out of office until Monday",
        from_address="eve@example.com",
        confidence=0.9,
        crm_store=crm,
    )
    assert crm.get_lead(ws, lead["id"])["stage"] == "contacted"


def test_low_confidence_queues_inbox(crm) -> None:
    ws = "ws443c"
    lead = crm.create_lead(ws, name="Fay", email="fay@example.com", stage="contacted")
    from keprix.crm.engagement import ingest_engagement, list_inbox

    result = ingest_engagement(
        workspace_id=ws,
        engagement_type="interested",
        body="maybe?",
        from_address="fay@example.com",
        confidence=0.4,
        crm_store=crm,
    )
    assert result["inbox_item"] is not None
    items = list_inbox(crm, ws, status="open")
    assert any(i.get("entity_id") == lead["id"] for i in items)
