"""Prompt 641: Soft Wall lifecycle, idempotency, events, receipts, drift."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from keprix.product_sidecar.control_plane import detect_projection_drift
from keprix.product_sidecar.connector import FakeProductConnector
from keprix.product_sidecar.generated import load_propreneur_connector_routes
from keprix.product_sidecar.packs.propreneur_ops import execute_propreneur_node
from keprix.product_sidecar.registry import get_product_pack_registry
from keprix.product_sidecar.routes import router
from keprix.product_sidecar.state import (
    get_approval_store,
    get_event_store,
    get_idempotency_ledger,
    get_receipt_store,
    input_hash,
    reset_all_sidecar_state_for_tests,
)
from keprix.product_sidecar.types import RequestContext


@pytest.fixture(autouse=True)
def _reset(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KEPRIX_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("KEPRIX_PRODUCT_SIDECAR_TOKEN_SECRET", "test-secret")
    monkeypatch.delenv("PROPRENEUR_PRODUCT_API_URL", raising=False)
    reset_all_sidecar_state_for_tests()
    get_product_pack_registry().reset_for_tests(install_fixtures=True)


def _ctx() -> RequestContext:
    return RequestContext(
        product="propreneur",
        deployment="test",
        workspace_id="ws-1",
        actor_id="user-1",
        grants=frozenset({"*"}),
        purpose="test",
        correlation_id="corr-641",
        session_id="sess-641",
    )


def _fake() -> FakeProductConnector:
    return FakeProductConnector(
        product_key="propreneur",
        extra_routes=list(load_propreneur_connector_routes().get("routes") or []),
    )


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def _auth_header() -> dict[str, str]:
    from keprix.product_sidecar.auth import get_token_service

    minted, _ = get_token_service().mint(
        product="propreneur",
        deployment="test",
        workspace_id="ws-1",
        actor_id="user-1",
        grants=frozenset({"*"}),
        purpose="invoke",
        ttl_seconds=60,
    )
    return {"Authorization": f"Bearer {minted}"}


@pytest.mark.asyncio
async def test_approve_reject_expire_revoke_and_no_duplicate_pending() -> None:
    store = get_approval_store()
    payload = {"name": "Flat"}
    ih = input_hash(payload)
    first = store.request(
        product="propreneur",
        workspace_id="ws-1",
        node_key="property_create",
        input_hash=ih,
        reason="test",
        deep_link="",
        actor_id="user-1",
    )
    second = store.request(
        product="propreneur",
        workspace_id="ws-1",
        node_key="property_create",
        input_hash=ih,
        reason="test",
        deep_link="",
        actor_id="user-1",
    )
    assert first["approval_id"] == second["approval_id"]

    approved = store.decide(
        first["approval_id"],
        workspace_id="ws-1",
        approved=True,
        actor_id="ops-1",
        input_hash=ih,
    )
    assert approved["status"] == "approved"
    # Duplicate approve callback is idempotent
    again = store.decide(
        first["approval_id"],
        workspace_id="ws-1",
        approved=True,
        actor_id="ops-1",
        input_hash=ih,
    )
    assert again["status"] == "approved"

    other = store.request(
        product="propreneur",
        workspace_id="ws-1",
        node_key="property_update",
        input_hash=input_hash({"propertyId": "1"}),
        reason="upd",
        deep_link="",
    )
    rejected = store.decide(
        other["approval_id"],
        workspace_id="ws-1",
        approved=False,
        actor_id="ops-1",
    )
    assert rejected["status"] == "rejected"

    pending = store.request(
        product="propreneur",
        workspace_id="ws-1",
        node_key="property_archive",
        input_hash=input_hash({"propertyId": "9"}),
        reason="arch",
        deep_link="",
    )
    expired = store.expire(pending["approval_id"], workspace_id="ws-1")
    assert expired["status"] == "expired"

    revocable = store.request(
        product="propreneur",
        workspace_id="ws-1",
        node_key="contact_create",
        input_hash=input_hash({"name": "A"}),
        reason="c",
        deep_link="",
    )
    store.decide(revocable["approval_id"], workspace_id="ws-1", approved=True, actor_id="ops-1")
    revoked = store.revoke(revocable["approval_id"], workspace_id="ws-1", actor_id="ops-1")
    assert revoked["status"] == "revoked"
    assert store.is_approved(revocable["approval_id"], workspace_id="ws-1", input_hash=input_hash({"name": "A"})) is False


@pytest.mark.asyncio
async def test_idempotency_replay_and_fingerprint_mismatch() -> None:
    fake = _fake()
    store = get_approval_store()
    body = {"name": "Idem Flat", "postcode": "E1 1AA"}
    ih = input_hash(body)
    row = store.request(
        product="propreneur",
        workspace_id="ws-1",
        node_key="property_create",
        input_hash=ih,
        reason="sw",
        deep_link="",
    )
    store.decide(row["approval_id"], workspace_id="ws-1", approved=True, actor_id="ops-1", input_hash=ih)

    first = await execute_propreneur_node(
        _ctx(),
        "property_create",
        {**body, "approval_id": row["approval_id"], "idempotency_key": "idem-641"},
        connector=fake,
    )
    assert first["success"] is True
    assert first["idempotency"]["state"] == "fresh"
    receipt_id = first["receipt_id"]

    second = await execute_propreneur_node(
        _ctx(),
        "property_create",
        {**body, "approval_id": row["approval_id"], "idempotency_key": "idem-641"},
        connector=fake,
    )
    assert second["success"] is True
    assert second["idempotency"]["state"] == "replay"
    assert second["receipt_id"] == receipt_id
    create_calls = [a for a in fake.actions if a.get("method") == "POST"]
    assert len(create_calls) == 1

    get_conflict = await execute_propreneur_node(
        _ctx(),
        "property_get",
        {"propertyId": "1", "idempotency_key": "idem-641"},
        connector=fake,
    )
    assert get_conflict["success"] is False
    assert get_conflict["status"] == "conflict"
    assert get_conflict["error"]["code"] == "idempotency_fingerprint_mismatch"


@pytest.mark.asyncio
async def test_retry_after_approval_and_etag_header() -> None:
    fake = _fake()
    pending = await execute_propreneur_node(
        _ctx(),
        "property_update",
        {"propertyId": "12", "name": "New", "if_match": "etag-v1"},
        connector=fake,
    )
    assert pending["status"] == "awaiting_approval"
    approval_id = pending["approval_id"]
    ih = pending["input_hash"]
    get_approval_store().decide(
        approval_id,
        workspace_id="ws-1",
        approved=True,
        actor_id="ops-1",
        input_hash=ih,
    )
    done = await execute_propreneur_node(
        _ctx(),
        "property_update",
        {
            "propertyId": "12",
            "name": "New",
            "if_match": "etag-v1",
            "approval_id": approval_id,
            "idempotency_key": "upd-1",
        },
        connector=fake,
    )
    assert done["success"] is True
    assert fake.actions[-1]["headers"].get("If-Match") == "etag-v1"
    assert done["receipt_id"]
    receipt = get_receipt_store().get(done["receipt_id"])
    assert receipt is not None
    assert receipt["approval_id"] == approval_id
    assert receipt["node_key"] == "property_update"
    assert "notes" not in str(receipt.get("result_summary"))


def test_duplicate_event_and_echo_suppression_and_ack() -> None:
    store = get_event_store()
    first = store.ingest(
        {
            "id": "evt-1",
            "type": "property.updated",
            "source": "propreneur",
            "product": "propreneur",
            "workspace_id": "ws-1",
            "data": {"id": "12"},
        }
    )
    assert first["deduped"] is False
    dup = store.ingest(
        {
            "id": "evt-1",
            "type": "property.updated",
            "source": "propreneur",
            "product": "propreneur",
            "workspace_id": "ws-1",
            "data": {"id": "12"},
        }
    )
    assert dup["deduped"] is True
    echo = store.ingest(
        {
            "id": "evt-echo",
            "type": "property.updated",
            "source": "propreneur",
            "product": "propreneur",
            "causation_id": "keprix:corr-641:property_update",
            "data": {"id": "12"},
        }
    )
    assert echo.get("echo_suppressed") is True
    ack = store.ack("evt-1", product="propreneur")
    assert ack["acked"] is True


def test_drift_detection_reports_without_overwrite() -> None:
    report = detect_projection_drift(
        product="propreneur",
        workspace_id="ws-1",
        contract_records=[{"id": "1", "version": "2"}, {"id": "2", "version": "1"}],
        projected_records=[{"id": "1", "version": "1"}, {"id": "3", "version": "1"}],
    )
    assert report["silent_overwrite"] is False
    assert report["source_of_truth"] == "propreneur"
    assert report["converged"] is False
    assert "1" in [m["record_id"] for m in report["version_mismatch"]]
    assert "2" in report["missing_in_projection"]
    assert "3" in report["extra_in_projection"]
    assert all(a["action"] != "overwrite_propreneur" for a in report["repair_actions"])


def test_http_approval_lifecycle_and_drift_routes() -> None:
    client = _client()
    headers = _auth_header()
    store = get_approval_store()
    row = store.request(
        product="propreneur",
        workspace_id="ws-1",
        node_key="property_create",
        input_hash=input_hash({"n": 1}),
        reason="http",
        deep_link="",
    )
    decision = client.post(
        f"/v1/products/propreneur/approvals/{row['approval_id']}/decision",
        headers=headers,
        json={
            "approved": True,
            "workspace_id": "ws-1",
            "actor_id": "ops-1",
            "input_hash": row["input_hash"],
        },
    )
    assert decision.status_code == 200
    status = client.get(
        f"/v1/products/propreneur/approvals/{row['approval_id']}",
        headers=headers,
        params={"workspace_id": "ws-1"},
    )
    assert status.status_code == 200
    assert status.json()["approval"]["status"] == "approved"

    pending = store.request(
        product="propreneur",
        workspace_id="ws-1",
        node_key="deal_create",
        input_hash=input_hash({"n": 2}),
        reason="http2",
        deep_link="",
    )
    expired = client.post(
        f"/v1/products/propreneur/approvals/{pending['approval_id']}/expire",
        headers=headers,
        json={"workspace_id": "ws-1", "actor_id": "ops-1"},
    )
    assert expired.status_code == 200
    assert expired.json()["approval"]["status"] == "expired"

    drift = client.post(
        "/v1/products/propreneur/projections/drift",
        headers=headers,
        json={
            "workspace_id": "ws-1",
            "contract_records": [{"id": "1", "etag": "a"}],
            "projected_records": [{"id": "1", "etag": "a"}],
        },
    )
    assert drift.status_code == 200
    assert drift.json()["converged"] is True

    # Duplicate event via HTTP
    e1 = client.post(
        "/v1/products/propreneur/events",
        headers=headers,
        json={
            "id": "http-evt-1",
            "type": "property.created",
            "source": "propreneur",
            "workspace_id": "ws-1",
            "data": {"id": "99"},
        },
    )
    assert e1.status_code == 200
    assert e1.json()["deduped"] is False
    e2 = client.post(
        "/v1/products/propreneur/events",
        headers=headers,
        json={
            "id": "http-evt-1",
            "type": "property.created",
            "source": "propreneur",
            "workspace_id": "ws-1",
            "data": {"id": "99"},
        },
    )
    assert e2.json()["deduped"] is True
    ack = client.post(
        "/v1/products/propreneur/events/http-evt-1/ack",
        headers=headers,
    )
    assert ack.status_code == 200
    assert ack.json()["acked"] is True
