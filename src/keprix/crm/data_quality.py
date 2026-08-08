"""Data freshness and quality dashboard (prompt 457)."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from keprix.crm.nice_schema import ensure_nice_schema
from keprix.crm.soft_wall import gate_or_approve


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def _primary_email(entity: dict[str, Any]) -> str | None:
    for item in entity.get("emails") or []:
        addr = item.get("address") if isinstance(item, dict) else item
        if addr:
            return str(addr)
    return None


def _primary_phone(entity: dict[str, Any]) -> str | None:
    for item in entity.get("phones") or []:
        num = item.get("number") if isinstance(item, dict) else item
        if num:
            return str(num)
    return None


def analyze_entity(store: Any, workspace_id: str, entity_type: str, entity: dict[str, Any], *, stale_days: int = 90) -> dict[str, Any]:
    ensure_nice_schema(store)
    ws = store._require_workspace(workspace_id)
    provenance = store.list_provenance(ws, entity_type=entity_type, entity_id=entity["id"])
    by_field: dict[str, list[dict[str, Any]]] = {}
    for p in provenance:
        by_field.setdefault(str(p.get("field_name")), []).append(p)

    incomplete: list[str] = []
    if not _primary_email(entity):
        incomplete.append("email")
    if not _primary_phone(entity):
        incomplete.append("phone")

    conflicts: list[dict[str, Any]] = []
    for field, rows in by_field.items():
        values = set()
        for r in rows:
            raw = r.get("value")
            if raw is None and r.get("value_json") is not None:
                raw = r.get("value_json")
            values.add(json.dumps(raw, sort_keys=True, default=str))
        if len(values) > 1:
            conflicts.append({"field": field, "sources": [r.get("adapter") for r in rows], "values": list(values)})

    unverified: list[str] = []
    stale_fields: list[str] = []
    cutoff = _utcnow() - timedelta(days=stale_days)
    for field, rows in by_field.items():
        for r in rows:
            state = str(r.get("verification_state") or "").lower()
            kind = str(r.get("kind") or "").lower()
            if state in {"unverified", ""} or kind in {"model_inferred", "derived"}:
                unverified.append(field)
            observed = r.get("observed_at") or r.get("created_at")
            if observed:
                try:
                    dt = datetime.fromisoformat(str(observed).replace("Z", "+00:00"))
                    if dt < cutoff:
                        stale_fields.append(field)
                except ValueError:
                    pass

    return {
        "entity_type": entity_type,
        "entity_id": entity["id"],
        "label": entity.get("name") or entity.get("display_name") or entity["id"],
        "stage": entity.get("stage"),
        "domain_pack": entity.get("domain_pack"),
        "owner_user_id": entity.get("owner_user_id"),
        "incomplete": sorted(set(incomplete)),
        "conflicts": conflicts,
        "unverified": sorted(set(unverified)),
        "stale_fields": sorted(set(stale_fields)),
        "is_stale": bool(stale_fields),
        "is_incomplete": bool(incomplete),
        "has_conflict": bool(conflicts),
    }


def quality_summary(
    store: Any,
    workspace_id: str,
    *,
    pack: str | None = None,
    stage: str | None = None,
    owner: str | None = None,
    stale_days: int = 90,
) -> dict[str, Any]:
    ensure_nice_schema(store)
    ws = store._require_workspace(workspace_id)
    findings: list[dict[str, Any]] = []
    for etype, lister in (("lead", store.list_leads), ("contact", store.list_contacts)):
        for entity in lister(ws, limit=1000):
            if pack and entity.get("domain_pack") != pack:
                continue
            if stage and entity.get("stage") != stage:
                continue
            if owner and entity.get("owner_user_id") != owner:
                continue
            findings.append(analyze_entity(store, ws, etype, entity, stale_days=stale_days))

    total = max(1, len(findings))
    incomplete = [f for f in findings if f["is_incomplete"]]
    stale = [f for f in findings if f["is_stale"]]
    conflicts = [f for f in findings if f["has_conflict"]]
    unverified = [f for f in findings if f["unverified"]]
    incomplete_email = [f for f in findings if "email" in f["incomplete"]]
    incomplete_phone = [f for f in findings if "phone" in f["incomplete"]]
    stale_pct = round(100.0 * len(stale) / total, 2)
    settings = get_nice_settings(store, ws)
    alert = stale_pct > float(settings.get("stale_alert_pct") or 40.0)
    return {
        "counts": {
            "total": len(findings),
            "incomplete": len(incomplete),
            "incomplete_email": len(incomplete_email),
            "incomplete_phone": len(incomplete_phone),
            "stale": len(stale),
            "conflicts": len(conflicts),
            "unverified": len(unverified),
        },
        "stale_pct": stale_pct,
        "alert": alert,
        "alert_message": f"Stale share {stale_pct}% exceeds threshold" if alert else None,
        "incomplete_email": incomplete_email[:100],
        "incomplete_phone": incomplete_phone[:100],
        "conflicts": conflicts[:100],
        "stale": stale[:100],
        "findings": findings[:200],
    }


def create_reverify_job(
    store: Any,
    workspace_id: str,
    *,
    filters: dict[str, Any] | None = None,
    actor_id: str | None = None,
    force: bool = False,
    approval_id: str | None = None,
) -> dict[str, Any]:
    ensure_nice_schema(store)
    ws = store._require_workspace(workspace_id)
    summary = quality_summary(store, ws, **(filters or {}))
    gate = gate_or_approve(
        ws,
        kind="data_quality_reverify",
        subject="Bulk re-verify CRM fields",
        payload={"filters": filters or {}, "counts": summary.get("counts")},
        object_type="data_quality_job",
        object_id=None,
        actor_id=actor_id,
        force=force,
        approval_id=approval_id,
    )
    if gate.get("blocked"):
        # Still create a proposed job linked to Soft Wall.
        rid = str(uuid.uuid4())
        with store._lock:
            store._conn.execute(
                """
                INSERT INTO crm_data_quality_jobs (
                    id, workspace_id, status, filters_json, findings_json, soft_wall_approval_id, actor_id, created_at, updated_at
                ) VALUES (?, ?, 'proposed', ?, ?, ?, ?, ?, ?)
                """,
                (
                    rid,
                    ws,
                    json.dumps(filters or {}),
                    json.dumps(summary.get("findings") or [], default=str),
                    (gate.get("approval") or {}).get("id"),
                    actor_id,
                    _iso(_utcnow()),
                    _iso(_utcnow()),
                ),
            )
            store._conn.commit()
        return {"ok": False, "blocked": True, "approval": gate.get("approval"), "job_id": rid}
    rid = str(uuid.uuid4())
    with store._lock:
        store._conn.execute(
            """
            INSERT INTO crm_data_quality_jobs (
                id, workspace_id, status, filters_json, findings_json, actor_id, created_at, updated_at
            ) VALUES (?, ?, 'queued', ?, ?, ?, ?, ?)
            """,
            (
                rid,
                ws,
                json.dumps(filters or {}),
                json.dumps(summary.get("findings") or [], default=str),
                actor_id,
                _iso(_utcnow()),
                _iso(_utcnow()),
            ),
        )
        store._conn.commit()
    return {"ok": True, "job_id": rid, "status": "queued", "summary": summary}


def get_nice_settings(store: Any, workspace_id: str) -> dict[str, Any]:
    ensure_nice_schema(store)
    ws = store._require_workspace(workspace_id)
    row = store._fetchone(
        "SELECT * FROM crm_workspace_nice_settings WHERE workspace_id = ?",
        (ws,),
    )
    if not row:
        return {
            "workspace_id": ws,
            "tracking_enabled": False,
            "whatsapp_sms_enabled": False,
            "voice_retention_days": 30,
            "voice_consent_required": True,
            "default_locale": "en-GB",
            "stale_alert_pct": 40.0,
            "settings": {},
        }
    out = dict(row)
    out["tracking_enabled"] = bool(out.get("tracking_enabled"))
    out["whatsapp_sms_enabled"] = bool(out.get("whatsapp_sms_enabled"))
    out["voice_consent_required"] = bool(out.get("voice_consent_required"))
    try:
        out["settings"] = json.loads(out.pop("settings_json", None) or "{}")
    except json.JSONDecodeError:
        out["settings"] = {}
    return out


def upsert_nice_settings(store: Any, workspace_id: str, **fields: Any) -> dict[str, Any]:
    ensure_nice_schema(store)
    ws = store._require_workspace(workspace_id)
    current = get_nice_settings(store, ws)
    merged = {**current, **fields}
    settings_json = json.dumps(merged.get("settings") or {}, default=str)
    with store._lock:
        store._conn.execute(
            """
            INSERT INTO crm_workspace_nice_settings (
                workspace_id, tracking_enabled, whatsapp_sms_enabled, voice_retention_days,
                voice_consent_required, default_locale, stale_alert_pct, settings_json, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(workspace_id) DO UPDATE SET
                tracking_enabled = excluded.tracking_enabled,
                whatsapp_sms_enabled = excluded.whatsapp_sms_enabled,
                voice_retention_days = excluded.voice_retention_days,
                voice_consent_required = excluded.voice_consent_required,
                default_locale = excluded.default_locale,
                stale_alert_pct = excluded.stale_alert_pct,
                settings_json = excluded.settings_json,
                updated_at = excluded.updated_at
            """,
            (
                ws,
                1 if merged.get("tracking_enabled") else 0,
                1 if merged.get("whatsapp_sms_enabled") else 0,
                int(merged.get("voice_retention_days") or 30),
                1 if merged.get("voice_consent_required", True) else 0,
                str(merged.get("default_locale") or "en-GB"),
                float(merged.get("stale_alert_pct") or 40.0),
                settings_json,
                _iso(_utcnow()),
            ),
        )
        store._conn.commit()
    return get_nice_settings(store, ws)
