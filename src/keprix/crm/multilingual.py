"""Multilingual nurture templates with Soft Wall locale review (prompt 458)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from keprix.crm.data_quality import get_nice_settings
from keprix.crm.nice_schema import ensure_nice_schema
from keprix.crm.soft_wall import gate_or_approve

COMPLIANCE_HINTS: dict[str, str] = {
    "en-GB": "UK PECR/GDPR defaults apply. Soft opt-in and LI assessments documented in compliance module. Not legal advice.",
    "en-US": "US CAN-SPAM style disclosures may apply. Confirm state rules. Not legal advice.",
    "fr-FR": "France / EU ePrivacy and CNIL expectations may apply. Confirm local counsel. Not legal advice.",
    "de-DE": "Germany / EU ePrivacy expectations may apply. Confirm local counsel. Not legal advice.",
    "es-ES": "Spain / EU ePrivacy expectations may apply. Confirm local counsel. Not legal advice.",
}


def _utcnow() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def compliance_hint(locale: str) -> str:
    return COMPLIANCE_HINTS.get(locale) or (
        f"Locale {locale}: confirm regional electronic marketing rules before enroll. Not legal advice."
    )


def upsert_locale_variant(
    store: Any,
    workspace_id: str,
    *,
    sequence_id: str,
    step_order: int,
    locale: str,
    subject: str | None,
    body: str | None,
    actor_id: str | None = None,
    force: bool = False,
    approval_id: str | None = None,
) -> dict[str, Any]:
    ensure_nice_schema(store)
    ws = store._require_workspace(workspace_id)
    existing = store._fetchone(
        """
        SELECT * FROM crm_template_locales
        WHERE workspace_id = ? AND sequence_id = ? AND step_order = ? AND locale = ?
        """,
        (ws, sequence_id, step_order, locale),
    )
    # Soft Wall required on first publish of each locale variant.
    if not existing or not existing.get("reviewed"):
        gate = gate_or_approve(
            ws,
            kind="locale_template_publish",
            subject=f"Review locale template {locale} step {step_order}",
            payload={
                "sequence_id": sequence_id,
                "step_order": step_order,
                "locale": locale,
                "subject": subject,
                "compliance_hint": compliance_hint(locale),
            },
            object_type="template_locale",
            object_id=f"{sequence_id}:{step_order}:{locale}",
            actor_id=actor_id,
            force=force,
            approval_id=approval_id,
        )
        if gate.get("blocked"):
            return {"ok": False, "blocked": True, "approval": gate.get("approval"), "compliance_hint": compliance_hint(locale)}
        reviewed = 1
    else:
        reviewed = int(existing.get("reviewed") or 0)

    rid = existing["id"] if existing else str(uuid.uuid4())
    now = _utcnow()
    with store._lock:
        if existing:
            store._conn.execute(
                """
                UPDATE crm_template_locales
                SET subject = ?, body = ?, reviewed = ?, compliance_hint = ?, actor_id = ?, updated_at = ?
                WHERE id = ?
                """,
                (subject, body, reviewed, compliance_hint(locale), actor_id, now, rid),
            )
        else:
            store._conn.execute(
                """
                INSERT INTO crm_template_locales (
                    id, workspace_id, sequence_id, step_order, locale, subject, body,
                    reviewed, compliance_hint, actor_id, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    rid,
                    ws,
                    sequence_id,
                    step_order,
                    locale,
                    subject,
                    body,
                    reviewed,
                    compliance_hint(locale),
                    actor_id,
                    now,
                    now,
                ),
            )
        store._conn.commit()
    return {"ok": True, "variant": get_locale_variant(store, ws, rid)}


def get_locale_variant(store: Any, workspace_id: str, variant_id: str) -> dict[str, Any] | None:
    ensure_nice_schema(store)
    ws = store._require_workspace(workspace_id)
    return store._fetchone(
        "SELECT * FROM crm_template_locales WHERE workspace_id = ? AND id = ?",
        (ws, variant_id),
    )


def list_locale_variants(store: Any, workspace_id: str, *, sequence_id: str | None = None) -> list[dict[str, Any]]:
    ensure_nice_schema(store)
    ws = store._require_workspace(workspace_id)
    if sequence_id:
        return store._fetchall(
            "SELECT * FROM crm_template_locales WHERE workspace_id = ? AND sequence_id = ? ORDER BY step_order, locale",
            (ws, sequence_id),
        )
    return store._fetchall(
        "SELECT * FROM crm_template_locales WHERE workspace_id = ? ORDER BY sequence_id, step_order, locale",
        (ws,),
    )


def resolve_step_copy(
    store: Any,
    workspace_id: str,
    *,
    sequence_id: str,
    step_order: int,
    preferred_locale: str | None,
    default_step: dict[str, Any] | None = None,
) -> dict[str, Any]:
    ensure_nice_schema(store)
    ws = store._require_workspace(workspace_id)
    settings = get_nice_settings(store, ws)
    fallback = str(settings.get("default_locale") or "en-GB")
    locales = [preferred_locale, fallback, "en-GB"]
    for locale in locales:
        if not locale:
            continue
        row = store._fetchone(
            """
            SELECT * FROM crm_template_locales
            WHERE workspace_id = ? AND sequence_id = ? AND step_order = ? AND locale = ?
            """,
            (ws, sequence_id, step_order, locale),
        )
        if row:
            if not row.get("reviewed"):
                return {
                    "ok": False,
                    "error": "locale_unreviewed",
                    "locale": locale,
                    "message": "Unreviewed locale cannot enroll",
                }
            return {
                "ok": True,
                "locale": locale,
                "subject": row.get("subject"),
                "body": row.get("body"),
                "fallback_used": locale != preferred_locale,
                "compliance_hint": row.get("compliance_hint"),
            }
    step = default_step or {}
    return {
        "ok": True,
        "locale": fallback,
        "subject": step.get("subject"),
        "body": step.get("body"),
        "fallback_used": True,
        "compliance_hint": compliance_hint(fallback),
    }


def can_enroll_locale(store: Any, workspace_id: str, *, sequence_id: str, locale: str) -> dict[str, Any]:
    variants = [
        v
        for v in list_locale_variants(store, workspace_id, sequence_id=sequence_id)
        if v.get("locale") == locale
    ]
    if not variants:
        return {"ok": True, "mode": "default_fallback"}
    if any(not v.get("reviewed") for v in variants):
        return {"ok": False, "error": "locale_unreviewed", "message": "Unreviewed locale cannot enroll"}
    return {"ok": True, "mode": "locale_variants"}


def analytics_by_locale(events: list[dict[str, Any]]) -> dict[str, Any]:
    buckets: dict[str, dict[str, int]] = {}
    for event in events:
        locale = str(event.get("locale") or "unknown")
        metric = str(event.get("metric") or event.get("type") or "event")
        bucket = buckets.setdefault(locale, {})
        bucket[metric] = int(bucket.get(metric) or 0) + int(event.get("count") or 1)
    return {"by_locale": buckets}
