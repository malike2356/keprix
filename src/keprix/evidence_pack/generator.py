"""Evidence pack zip assembly."""

from __future__ import annotations

import io
import json
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any

from keprix.evidence_pack.collector import collect_audit_events, collect_linked_documents, export_audit_csv
from keprix.evidence_pack.manifest import VERIFY_TXT, build_manifest, manifest_json_bytes, sha256_bytes
from keprix.evidence_pack.store import get_evidence_pack_store
from keprix.governance.audit_events import emit_audit_event
from keprix.governance.store import get_governance_store


def build_evidence_zip(
    *,
    pack_id: str,
    workspace_id: str,
    instance_id: str,
    date_from: datetime,
    date_to: datetime,
    events: list[dict[str, Any]],
    documents: list[tuple[str, bytes]],
    audit_csv: str,
) -> bytes:
    events_sha256: dict[str, str] = {}
    documents_sha256: dict[str, str] = {}
    included_types = sorted({str(event.get("event_type")) for event in events if event.get("event_type")})

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for event in events:
            event_id = str(event["event_id"])
            raw = json.dumps(event, indent=2, sort_keys=True).encode("utf-8")
            arcname = f"evidence-pack-{pack_id}/events/{event_id}.json"
            zf.writestr(arcname, raw)
            events_sha256[event_id] = sha256_bytes(raw)

        for filename, content in documents:
            arcname = f"evidence-pack-{pack_id}/documents/{filename}"
            zf.writestr(arcname, content)
            documents_sha256[filename] = sha256_bytes(content)

        zf.writestr(f"evidence-pack-{pack_id}/audit_extract.csv", audit_csv)
        zf.writestr(f"evidence-pack-{pack_id}/VERIFY.txt", VERIFY_TXT)

        manifest = build_manifest(
            pack_id=pack_id,
            workspace_id=workspace_id,
            instance_id=instance_id,
            date_from=date_from.isoformat().replace("+00:00", "Z"),
            date_to=date_to.isoformat().replace("+00:00", "Z"),
            events_sha256=events_sha256,
            documents_sha256=documents_sha256,
            included_event_types=included_types,
        )
        zf.writestr(
            f"evidence-pack-{pack_id}/manifest.json",
            manifest_json_bytes(manifest),
        )

    return buffer.getvalue()


async def generate_evidence_pack(
    *,
    workspace_id: str,
    date_from: datetime,
    date_to: datetime,
    event_types: list[str] | None = None,
    include_documents: bool = True,
    domain_pack: str | None = None,
) -> str:
    store = get_evidence_pack_store()
    included = event_types or []
    record = store.create_pending(
        workspace_id=workspace_id,
        date_from=date_from.isoformat().replace("+00:00", "Z"),
        date_to=date_to.isoformat().replace("+00:00", "Z"),
        included_event_types=included,
    )
    pack_id = record.pack_id
    try:
        events = await collect_audit_events(
            workspace_id,
            date_from,
            date_to,
            event_types=event_types,
            domain_pack=domain_pack,
        )
        documents: list[tuple[str, bytes]] = []
        if include_documents:
            documents = await collect_linked_documents(workspace_id, events)
        audit_csv = await export_audit_csv(workspace_id, date_from, date_to)
        gov_cfg = await get_governance_store().get_config()
        instance_id = str(gov_cfg.get("instance_id") or "local-instance")
        zip_bytes = build_evidence_zip(
            pack_id=pack_id,
            workspace_id=workspace_id,
            instance_id=instance_id,
            date_from=date_from,
            date_to=date_to,
            events=events,
            documents=documents,
            audit_csv=audit_csv,
        )
        zip_path = store._dir / f"{pack_id}.zip"
        zip_path.write_bytes(zip_bytes)
        manifest_sig = ""
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            manifest_raw = zf.read(f"evidence-pack-{pack_id}/manifest.json")
            manifest = json.loads(manifest_raw.decode("utf-8"))
            manifest_sig = str(manifest.get("manifest_signature") or "")

        store.mark_ready(
            pack_id,
            event_count=len(events),
            document_count=len(documents),
            zip_path=str(zip_path),
            manifest_signature=manifest_sig,
        )
        await emit_audit_event(
            "evidence_pack_generated",
            workspace_id=workspace_id,
            actor_type="system",
            summary=f"Evidence pack generated for period {date_from.date()} to {date_to.date()}",
            detail={
                "pack_id": pack_id,
                "pack_sha256": sha256_bytes(zip_bytes),
                "event_count": len(events),
                "date_from": date_from.isoformat().replace("+00:00", "Z"),
                "date_to": date_to.isoformat().replace("+00:00", "Z"),
                "included_types": sorted({e.get("event_type") for e in events}),
            },
            severity="info",
            domain_pack=domain_pack,
        )
        return pack_id
    except Exception:
        store.mark_failed(pack_id)
        raise


async def send_pack_to_provider(pack_id: str, *, api_key: str | None = None) -> dict[str, Any]:
    import httpx

    store = get_evidence_pack_store()
    record = store.get(pack_id)
    if record is None:
        raise ValueError("Evidence pack not found")
    zip_path = store.zip_path(pack_id)
    if zip_path is None:
        raise ValueError("Evidence pack file missing")

    gov_store = get_governance_store()
    cfg = await gov_store.get_config()
    if not cfg.get("enabled") or not cfg.get("provider_endpoint"):
        raise GovernanceProviderNotConnectedError(
            "Governance provider is not connected. Configure it in settings > governance."
        )

    body = zip_path.read_bytes()
    url = f"{str(cfg['provider_endpoint']).rstrip('/')}/api/v1/evidence-packs"
    headers = {
        "Authorization": f"Bearer {api_key or ''}",
        "Content-Type": "application/zip",
        "X-Pack-ID": pack_id,
        "X-Workspace-ID": record.workspace_id,
        "X-Instance-ID": str(cfg.get("instance_id") or ""),
        "X-Manifest-Signature": record.manifest_signature or "",
    }
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(url, content=body, headers=headers)
    if response.status_code >= 400:
        raise ValueError(f"Governance provider upload failed: HTTP {response.status_code}")
    payload = response.json()
    submission_id = str(payload.get("submission_id") or "")
    provider_endpoint = str(payload.get("provider_pack_url") or "")
    store.set_provider_submission(pack_id, submission_id, provider_endpoint)
    await emit_audit_event(
        "evidence_pack_exported",
        workspace_id=record.workspace_id,
        actor_type="system",
        summary=f"Evidence pack {pack_id} sent to governance provider",
        detail={"pack_id": pack_id, "provider_submission_id": submission_id},
        subject_type="evidence_pack",
        subject_id=pack_id,
    )
    return {"provider_submission_id": submission_id, "provider_pack_url": provider_endpoint}


class GovernanceProviderNotConnectedError(Exception):
    pass


# Backward-compatible alias for older imports.
ScoutNotConnectedError = GovernanceProviderNotConnectedError
