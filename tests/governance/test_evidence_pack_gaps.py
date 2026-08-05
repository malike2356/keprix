"""Evidence pack route and generator gap coverage (prompt 111)."""

from __future__ import annotations

import json
import zipfile
from datetime import datetime, timedelta, timezone
from io import BytesIO
from pathlib import Path

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from keprix.evidence_pack.generator import (
    GovernanceProviderNotConnectedError,
    build_evidence_zip,
    send_pack_to_provider,
)
from keprix.evidence_pack.routes import router as evidence_pack_router
from keprix.evidence_pack.store import EvidencePackStore, reset_evidence_pack_store
from keprix.governance.audit_events import sign_event
from keprix.governance.audit_store import AuditEventStore, reset_audit_event_store
from keprix.governance.store import GovernanceStore


@pytest.fixture()
def pack_env(tmp_path, monkeypatch):
    monkeypatch.setenv("KEPRIX_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("AUTH_ENABLED", "false")
    reset_audit_event_store()
    reset_evidence_pack_store()
    audit_store = AuditEventStore(base_dir=tmp_path / "audit_events")
    monkeypatch.setattr("keprix.governance.audit_store.get_audit_event_store", lambda: audit_store)
    monkeypatch.setattr("keprix.governance.audit_events.get_audit_event_store", lambda: audit_store)
    monkeypatch.setattr("keprix.evidence_pack.collector.get_audit_event_store", lambda: audit_store)
    pack_store = EvidencePackStore(base_dir=tmp_path / "evidence_packs")
    monkeypatch.setattr("keprix.evidence_pack.store.get_evidence_pack_store", lambda: pack_store)
    monkeypatch.setattr("keprix.evidence_pack.generator.get_evidence_pack_store", lambda: pack_store)
    monkeypatch.setattr("keprix.evidence_pack.routes.get_evidence_pack_store", lambda: pack_store)
    gov = GovernanceStore(base_dir=tmp_path / "scout")
    monkeypatch.setattr("keprix.governance.store.get_governance_store", lambda: gov)
    monkeypatch.setattr("keprix.evidence_pack.generator.get_governance_store", lambda: gov)
    return {"pack_store": pack_store, "gov": gov, "tmp": tmp_path}


def _event(i: int, now: datetime) -> dict:
    event = {
        "event_id": f"evt-{i}",
        "event_type": "compliance_scan_complete",
        "workspace_id": "default",
        "instance_id": "inst-1",
        "timestamp": (now - timedelta(minutes=i)).isoformat().replace("+00:00", "Z"),
        "actor_type": "system",
        "actor_id": None,
        "subject_type": None,
        "subject_id": None,
        "summary": f"event {i}",
        "detail": {},
        "severity": "info",
        "domain_pack": None,
        "signature": "",
    }
    event["signature"] = sign_event(event)
    return event


def test_pack_with_20_events_produces_20_json_files(pack_env) -> None:
    now = datetime.now(timezone.utc)
    events = [_event(i, now) for i in range(20)]
    zip_bytes = build_evidence_zip(
        pack_id="pack-20",
        workspace_id="default",
        instance_id="inst-1",
        date_from=now - timedelta(days=1),
        date_to=now,
        events=events,
        documents=[],
        audit_csv="event_id,event_type\n",
    )
    with zipfile.ZipFile(BytesIO(zip_bytes)) as zf:
        event_files = [name for name in zf.namelist() if "/events/" in name and name.endswith(".json")]
    assert len(event_files) == 20


@pytest.mark.asyncio
async def test_list_evidence_packs_route(pack_env) -> None:
    store: EvidencePackStore = pack_env["pack_store"]
    record = store.create_pending(
        workspace_id="default",
        date_from="2026-01-01T00:00:00Z",
        date_to="2026-01-08T00:00:00Z",
        included_event_types=["compliance_scan_complete"],
    )
    zip_path = Path(pack_env["tmp"]) / "evidence_packs" / f"{record.pack_id}.zip"
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    zip_path.write_bytes(b"PK\x03\x04")
    store.mark_ready(
        record.pack_id,
        event_count=3,
        document_count=0,
        zip_path=str(zip_path),
        manifest_signature="sig",
    )

    app = FastAPI()
    app.include_router(evidence_pack_router)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/evidence-pack")
    assert response.status_code == 200
    packs = response.json()["packs"]
    assert len(packs) == 1
    assert packs[0]["status"] == "ready"
    assert packs[0]["event_count"] == 3


@pytest.mark.asyncio
async def test_send_to_provider_returns_409_when_disconnected(pack_env) -> None:
    store: EvidencePackStore = pack_env["pack_store"]
    record = store.create_pending(
        workspace_id="default",
        date_from="2026-01-01T00:00:00Z",
        date_to="2026-01-08T00:00:00Z",
        included_event_types=[],
    )
    zip_path = Path(pack_env["tmp"]) / "evidence_packs" / f"{record.pack_id}.zip"
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    zip_path.write_bytes(b"PK\x03\x04")
    store.mark_ready(
        record.pack_id,
        event_count=1,
        document_count=0,
        zip_path=str(zip_path),
        manifest_signature="sig",
    )
    with pytest.raises(GovernanceProviderNotConnectedError):
        await send_pack_to_provider(record.pack_id)

    app = FastAPI()
    app.include_router(evidence_pack_router)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(f"/api/evidence-pack/{record.pack_id}/send-to-provider")
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_send_to_provider_returns_submission_id(pack_env, monkeypatch) -> None:
    store: EvidencePackStore = pack_env["pack_store"]
    gov: GovernanceStore = pack_env["gov"]
    await gov.save_config(
        {
            "enabled": True,
            "provider_endpoint": "https://provider.example",
            "instance_id": "inst-1",
        }
    )
    record = store.create_pending(
        workspace_id="default",
        date_from="2026-01-01T00:00:00Z",
        date_to="2026-01-08T00:00:00Z",
        included_event_types=[],
    )
    zip_path = Path(pack_env["tmp"]) / "evidence_packs" / f"{record.pack_id}.zip"
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    zip_path.write_bytes(b"PK\x03\x04fakezip")
    store.mark_ready(
        record.pack_id,
        event_count=1,
        document_count=0,
        zip_path=str(zip_path),
        manifest_signature="sig",
    )

    class _Resp:
        status_code = 200

        def json(self):
            return {
                "submission_id": "sub-123",
                "provider_pack_url": "https://provider.example/packs/sub-123",
            }

    class _Client:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def post(self, *args, **kwargs):
            return _Resp()

    monkeypatch.setattr("httpx.AsyncClient", _Client)

    async def _noop_emit(*args, **kwargs):
        return "evt"

    monkeypatch.setattr("keprix.evidence_pack.generator.emit_audit_event", _noop_emit)

    result = await send_pack_to_provider(record.pack_id)
    assert result["provider_submission_id"] == "sub-123"
    updated = store.get(record.pack_id)
    assert updated is not None
    assert updated.provider_submission_id == "sub-123"
