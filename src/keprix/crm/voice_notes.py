"""Voice notes and call notes as CRM activities (prompt 462)."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from keprix.crm.data_quality import get_nice_settings
from keprix.crm.nice_schema import ensure_nice_schema
from keprix.crm.soft_wall import gate_or_approve


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def create_call_note(
    store: Any,
    workspace_id: str,
    *,
    entity_type: str,
    entity_id: str,
    duration_seconds: int | None = None,
    outcome: str | None = None,
    next_step: str | None = None,
    body: str | None = None,
    actor_id: str | None = None,
) -> dict[str, Any]:
    activity = store.create_activity(
        workspace_id,
        entity_type=entity_type,
        entity_id=entity_id,
        activity_type="call_note",
        channel="phone",
        subject=f"Call note: {outcome or 'logged'}",
        body=body or "",
        metadata={
            "duration_seconds": duration_seconds,
            "outcome": outcome,
            "next_step": next_step,
        },
        actor_type="user",
        actor_id=actor_id,
    )
    return {"ok": True, "activity": activity}


def attach_voice_note(
    store: Any,
    workspace_id: str,
    *,
    entity_type: str | None,
    entity_id: str | None,
    media_path: str | None = None,
    transcript: str | None = None,
    stt_configured: bool = False,
    consent_recorded: bool = False,
    actor_id: str | None = None,
) -> dict[str, Any]:
    ensure_nice_schema(store)
    ws = store._require_workspace(workspace_id)
    if not entity_type or not entity_id:
        return {
            "ok": False,
            "error": "unlinked_chat",
            "message": "Unlinked chats do not invent CRM targets. Tag a lead/contact first.",
        }
    settings = get_nice_settings(store, ws)
    if settings.get("voice_consent_required") and not consent_recorded:
        return {
            "ok": False,
            "error": "voice_consent_required",
            "message": "Workspace requires consent/disclosure before storing voice media.",
        }
    text = transcript
    if stt_configured and not text and media_path:
        text = f"[stt stub transcript for {Path(media_path).name}]"
    activity = store.create_activity(
        ws,
        entity_type=entity_type,
        entity_id=entity_id,
        activity_type="voice_note",
        channel="telegram",
        subject="Voice note",
        body=text or "",
        metadata={"media_path": media_path, "stt_configured": stt_configured},
        actor_type="user",
        actor_id=actor_id,
    )
    retention_days = int(settings.get("voice_retention_days") or 30)
    retention_until = _iso(_utcnow() + timedelta(days=retention_days))
    rid = str(uuid.uuid4())
    with store._lock:
        store._conn.execute(
            """
            INSERT INTO crm_voice_media (
                id, workspace_id, activity_id, entity_type, entity_id, media_path, transcript,
                retention_until, consent_recorded, actor_id, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                rid,
                ws,
                activity["id"],
                entity_type,
                entity_id,
                media_path,
                text,
                retention_until,
                1 if consent_recorded else 0,
                actor_id,
                _iso(_utcnow()),
            ),
        )
        store._conn.commit()
    media = store._fetchone("SELECT * FROM crm_voice_media WHERE id = ?", (rid,))
    return {"ok": True, "activity": activity, "media": media}


def share_transcript_outside(
    store: Any,
    workspace_id: str,
    media_id: str,
    *,
    actor_id: str | None = None,
    force: bool = False,
    approval_id: str | None = None,
) -> dict[str, Any]:
    ensure_nice_schema(store)
    ws = store._require_workspace(workspace_id)
    media = store._fetchone(
        "SELECT * FROM crm_voice_media WHERE workspace_id = ? AND id = ?",
        (ws, media_id),
    )
    if not media:
        return {"ok": False, "error": "not_found"}
    gate = gate_or_approve(
        ws,
        kind="voice_transcript_share",
        subject="Share voice transcript outside workspace",
        payload={"media_id": media_id},
        object_type="voice_media",
        object_id=media_id,
        actor_id=actor_id,
        force=force,
        approval_id=approval_id,
    )
    if gate.get("blocked"):
        return {"ok": False, "blocked": True, "approval": gate.get("approval")}
    return {"ok": True, "media": media, "shared": True}


def run_retention_job(store: Any, workspace_id: str | None = None) -> dict[str, Any]:
    ensure_nice_schema(store)
    now = _iso(_utcnow())
    params: list[Any] = [now]
    sql = """
        SELECT * FROM crm_voice_media
        WHERE deleted_at IS NULL AND retention_until IS NOT NULL AND retention_until < ?
    """
    if workspace_id:
        sql += " AND workspace_id = ?"
        params.append(workspace_id)
    rows = store._fetchall(sql, tuple(params))
    deleted = 0
    for row in rows:
        path = row.get("media_path")
        if path:
            try:
                p = Path(path)
                if p.exists() and p.is_file():
                    p.unlink()
            except OSError:
                pass
        with store._lock:
            store._conn.execute(
                "UPDATE crm_voice_media SET deleted_at = ?, media_path = NULL WHERE id = ?",
                (now, row["id"]),
            )
            store._conn.commit()
        deleted += 1
    return {"ok": True, "deleted": deleted}
