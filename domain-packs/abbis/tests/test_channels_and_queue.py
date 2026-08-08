"""Channel idempotency, confirmation gates, RAG tenant isolation, degraded queue."""

from __future__ import annotations

import sys
from pathlib import Path

PACK_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACK_ROOT))

from channels import (  # noqa: E402
    confirmation_gate,
    ingest_channel_message,
    rag_retrieve,
    reset_channel_state,
    voice_workflow_contract,
)
from ai_queue.degraded import degraded_queue  # noqa: E402


def setup_function() -> None:
    reset_channel_state()
    degraded_queue.reset()


def test_voice_workflows_vw1_vw7() -> None:
    for wid in ("vw1", "vw2", "vw3", "vw4", "vw5", "vw6", "vw7"):
        assert voice_workflow_contract(wid)["requires_product_context"] is True


def test_spoken_numbers_require_confirmation() -> None:
    gate = confirmation_gate(intent="financial", spoken_or_typed="Pay 80 GHS for 2 pipes", confirmed=False)
    assert gate["allowed"] is False
    assert gate["reason"] == "numbers_units_unconfirmed"


def test_channel_delivery_idempotent() -> None:
    links = {"whatsapp:+233111": {"tenant_id": "tenant-alpha", "actor_id": "u1", "chat_type": "private"}}
    first = ingest_channel_message(
        channel="whatsapp",
        delivery_id="d1",
        external_id="+233111",
        text="status please",
        links=links,
        intent="read",
        confirmed=True,
    )
    second = ingest_channel_message(
        channel="whatsapp",
        delivery_id="d1",
        external_id="+233111",
        text="status please",
        links=links,
        intent="read",
        confirmed=True,
    )
    assert first["status"] == "accepted"
    assert second["status"] == "deduped"


def test_group_chat_blocks_sensitive() -> None:
    links = {"whatsapp:g1": {"tenant_id": "tenant-alpha", "actor_id": "u1", "chat_type": "group"}}
    out = ingest_channel_message(
        channel="whatsapp",
        delivery_id="d2",
        external_id="g1",
        text="pay worker 100 GHS",
        links=links,
        intent="financial",
        confirmed=True,
    )
    assert out["status"] == "denied"


def test_rag_cannot_cross_tenant() -> None:
    corpora = [
        {"id": "1", "tenant_id": "tenant-alpha", "accessory": "field.operations", "authority": "verified_record", "citation": "a"},
        {"id": "2", "tenant_id": "tenant-beta", "accessory": "field.operations", "authority": "verified_record", "citation": "b"},
        {"id": "3", "tenant_id": "public", "accessory": "field.operations", "authority": "standard", "scope": "public", "citation": "c"},
    ]
    hits = rag_retrieve(query="", tenant_id="tenant-alpha", accessory="field.operations", corpora=corpora)
    ids = {h["id"] for h in hits}
    assert "1" in ids
    assert "3" in ids
    assert "2" not in ids


def test_offline_queue_rejects_stale_authority() -> None:
    item = degraded_queue.enqueue(
        tenant_id="tenant-alpha",
        actor_id="u1",
        node_key="drilling_log_assist",
        payload={"ref": "log-1"},
        dedupe_key="log-1",
        authority_version="v1",
        record_version=3,
        approval_id="appr_1",
        low_bandwidth=True,
    )
    replay = degraded_queue.replay(
        item["id"],
        current_authority_version="v2",
        current_record_version=3,
        approval_still_valid=True,
        permissions_ok=True,
    )
    assert replay["status"] == "rejected_stale_authority"
