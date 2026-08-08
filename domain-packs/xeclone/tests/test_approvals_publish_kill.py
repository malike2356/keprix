"""Approvals, publish once, kill switch, and private reply tests."""

from __future__ import annotations

import sys
from pathlib import Path

from fastapi.testclient import TestClient

PACK_ROOT = Path(__file__).resolve().parents[1]


def _client() -> TestClient:
    if str(PACK_ROOT) not in sys.path:
        sys.path.insert(0, str(PACK_ROOT))
    import http_app
    from approvals.service import reset_approvals
    from channels.outbox import reset_channels
    from kill_switch.state import reset_kill_switch

    reset_approvals()
    reset_channels()
    reset_kill_switch()
    return TestClient(http_app.app)


def test_approve_once_publish_once() -> None:
    client = _client()
    draft = client.post(
        "/v1/products/xeclone/bridge/draft",
        json={"content": "Publish me once", "channel": "web", "tenant": "owner-laud"},
    )
    assert draft.status_code == 200
    approval = draft.json()["approval"]
    approval_id = approval["approval_id"]
    content_hash = approval["content_hash"]

    decided = client.post(
        f"/v1/products/xeclone/approvals/{approval_id}/decision",
        json={"approved": True, "actor_id": "owner", "content_hash": content_hash},
    )
    assert decided.status_code == 200
    assert decided.json()["status"] == "approved"

    pub1 = client.post(
        "/v1/products/xeclone/publish",
        json={
            "approval_id": approval_id,
            "idempotency_key": "idem-1",
            "channel": "web",
            "tenant_id": "owner-laud",
        },
    )
    assert pub1.status_code == 200
    assert pub1.json()["deduped"] is False

    # Retry same idempotency key does not double-post
    pub2 = client.post(
        "/v1/products/xeclone/publish",
        json={
            "approval_id": approval_id,
            "idempotency_key": "idem-1",
            "channel": "web",
            "tenant_id": "owner-laud",
        },
    )
    assert pub2.status_code == 200
    assert pub2.json()["deduped"] is True

    # Different key but same approval cannot publish again
    pub3 = client.post(
        "/v1/products/xeclone/publish",
        json={
            "approval_id": approval_id,
            "idempotency_key": "idem-2",
            "channel": "web",
            "tenant_id": "owner-laud",
        },
    )
    assert pub3.status_code == 400


def test_kill_switch_stops_publish() -> None:
    client = _client()
    draft = client.post(
        "/v1/products/xeclone/bridge/draft",
        json={"content": "Blocked publish", "channel": "web"},
    ).json()["approval"]
    client.post(
        f"/v1/products/xeclone/approvals/{draft['approval_id']}/decision",
        json={"approved": True, "actor_id": "owner", "content_hash": draft["content_hash"]},
    )
    ks = client.post(
        "/v1/products/xeclone/kill-switch",
        json={"active": True, "scopes": ["publish", "media"], "reason": "test"},
    )
    assert ks.status_code == 200
    assert client.get("/v1/products/xeclone/kill-switch").json()["active"] is True
    blocked = client.post(
        "/v1/products/xeclone/publish",
        json={
            "approval_id": draft["approval_id"],
            "idempotency_key": "ks-1",
            "channel": "web",
        },
    )
    assert blocked.status_code == 400
    assert "kill_switch" in str(blocked.json()).lower()


def test_material_edit_invalidates() -> None:
    client = _client()
    if str(PACK_ROOT) not in sys.path:
        sys.path.insert(0, str(PACK_ROOT))
    from approvals.service import apply_material_edit, submit_preview

    row = submit_preview(
        content="original",
        channel="web",
        audience="public",
        persona_version="ilaud@0.1.0",
    )
    apply_material_edit(row["approval_id"], "edited content")
    decided = client.post(
        f"/v1/products/xeclone/approvals/{row['approval_id']}/decision",
        json={"approved": True, "actor_id": "owner", "content_hash": row["content_hash"]},
    )
    assert decided.status_code == 400


def test_private_reply_owner_reviewed() -> None:
    client = _client()
    inv = client.post(
        "/v1/products/xeclone/invoke",
        json={"capability": "private_reply_send", "input": {"content": "hi"}},
    )
    assert inv.status_code == 200
    result = inv.json()["result"]
    assert result["draft_only"] is True
    assert result["owner_reviewed_required"] is True

    denied = client.post(
        "/v1/products/xeclone/invoke",
        json={
            "capability": "private_reply_send",
            "input": {"policy_allows_send": True, "owner_reviewed": False, "approval_id": "x"},
        },
    )
    assert denied.status_code == 400
