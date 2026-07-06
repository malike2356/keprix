"""Clinical event tests."""

from __future__ import annotations

import json
import zipfile
from datetime import datetime, timedelta, timezone
from io import BytesIO

import pytest

from keprix.evidence_pack.generator import build_evidence_zip, generate_evidence_pack
from keprix.evidence_pack.manifest import verify_manifest_signature
from keprix.evidence_pack.store import reset_evidence_pack_store
from keprix.governance.audit_events import (
    AUDIT_EVENT_TYPES,
    emit_audit_event,
    sign_event,
    verify_event_signature,
)
from keprix.governance.audit_store import reset_audit_event_store
from keprix.governance.store import GovernanceStore


@pytest.fixture(autouse=True)
def reset_stores(tmp_path, monkeypatch):
    monkeypatch.setenv("KEPRIX_DATA_DIR", str(tmp_path))
    reset_audit_event_store()
    reset_evidence_pack_store()
    from keprix.governance.audit_store import AuditEventStore

    audit_store = AuditEventStore(base_dir=tmp_path / "audit_events")
    monkeypatch.setattr("keprix.governance.audit_store.get_audit_event_store", lambda: audit_store)
    monkeypatch.setattr("keprix.governance.audit_events.get_audit_event_store", lambda: audit_store)
    monkeypatch.setattr("keprix.evidence_pack.collector.get_audit_event_store", lambda: audit_store)
    store = GovernanceStore(base_dir=tmp_path / "scout")
    monkeypatch.setattr("keprix.governance.store.get_governance_store", lambda: store)
    monkeypatch.setattr("keprix.governance.audit_events.get_governance_store", lambda: store)
    monkeypatch.setattr("keprix.governance.event_reporter.get_governance_store", lambda: store)
    from keprix.evidence_pack.store import EvidencePackStore

    pack_store = EvidencePackStore(base_dir=tmp_path / "evidence_packs")
    monkeypatch.setattr("keprix.evidence_pack.store.get_evidence_pack_store", lambda: pack_store)
    monkeypatch.setattr("keprix.evidence_pack.generator.get_evidence_pack_store", lambda: pack_store)


@pytest.mark.asyncio
async def test_invalid_event_type_raises() -> None:
    with pytest.raises(ValueError, match="Invalid clinical event_type"):
        await emit_audit_event(
            "not_a_real_event",
            workspace_id="default",
            actor_type="system",
            summary="bad",
        )


@pytest.mark.asyncio
async def test_emit_audit_event_signs_and_stores() -> None:
    event_id = await emit_audit_event(
        "compliance_scan_complete",
        workspace_id="default",
        actor_type="system",
        summary="Scan finished",
        detail={"scan_id": "scan-1", "findings_count": 0},
    )
    assert event_id
    from keprix.governance.audit_store import get_audit_event_store

    rows = get_audit_event_store().list_events("default")
    assert len(rows) == 1
    assert rows[0]["event_type"] == "compliance_scan_complete"
    assert verify_event_signature(rows[0])


def test_all_prompt_event_types_registered() -> None:
    for key in (
        "cso_review_approved",
        "evidence_pack_generated",
        "gdpr_dsar_requested",
        "legal_acceptance_recorded",
        "pack_gate_approved",
    ):
        assert key in AUDIT_EVENT_TYPES


@pytest.mark.asyncio
async def test_evidence_pack_zip_manifest_hashes_match() -> None:
    now = datetime.now(timezone.utc)
    event = {
        "event_id": "evt-1",
        "event_type": "compliance_scan_complete",
        "workspace_id": "default",
        "instance_id": "inst-1",
        "timestamp": now.isoformat().replace("+00:00", "Z"),
        "actor_type": "system",
        "actor_id": None,
        "subject_type": None,
        "subject_id": None,
        "summary": "done",
        "detail": {},
        "severity": "info",
        "domain_pack": None,
        "signature": "",
    }
    event["signature"] = sign_event(event)
    zip_bytes = build_evidence_zip(
        pack_id="pack-1",
        workspace_id="default",
        instance_id="inst-1",
        date_from=now - timedelta(days=1),
        date_to=now,
        events=[event],
        documents=[],
        audit_csv="event_id,event_type\n",
    )
    with zipfile.ZipFile(BytesIO(zip_bytes)) as zf:
        manifest = json.loads(zf.read("evidence-pack-pack-1/manifest.json"))
        assert verify_manifest_signature(manifest)
        event_bytes = zf.read("evidence-pack-pack-1/events/evt-1.json")
        assert manifest["events_sha256"]["evt-1"] == __import__("hashlib").sha256(event_bytes).hexdigest()


@pytest.mark.asyncio
async def test_generate_evidence_pack_counts_events() -> None:
    await emit_audit_event(
        "gdpr_dsar_requested",
        workspace_id="ws-1",
        actor_type="user",
        actor_id="u1",
        summary="dsar",
    )
    now = datetime.now(timezone.utc)
    pack_id = await generate_evidence_pack(
        workspace_id="ws-1",
        date_from=now - timedelta(days=1),
        date_to=now + timedelta(minutes=1),
    )
    from keprix.evidence_pack.store import get_evidence_pack_store

    record = get_evidence_pack_store().get(pack_id)
    assert record is not None
    assert record.status == "ready"
    assert record.event_count >= 1
