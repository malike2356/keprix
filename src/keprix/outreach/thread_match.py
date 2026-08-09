"""Workspace-scoped outbound matching for inbound outreach replies (Prompt 626)."""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any

from keprix.outreach.inbound_mail import strip_angle_brackets

# Correlation / reply token e.g. [kp-abc123] or kp-abc123
_CORRELATION_TOKEN_RE = re.compile(r"\[?\s*(kp-[a-zA-Z0-9_-]{4,64})\s*\]?", re.I)

MATCHED = "matched"
AMBIGUOUS = "ambiguous"
UNMATCHED = "unmatched"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        raw = str(value).replace("Z", "+00:00")
        dt = datetime.fromisoformat(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def extract_correlation_tokens(subject: str, body: str) -> list[str]:
    text = f"{subject or ''}\n{body or ''}"
    found: list[str] = []
    for match in _CORRELATION_TOKEN_RE.finditer(text):
        token = match.group(1).lower()
        if token not in found:
            found.append(token)
    return found


def _message_refs(message: dict[str, Any]) -> dict[str, Any]:
    enrollment_id = message.get("enrollment_id")
    lead_id = None
    campaign_id = None
    sequence_id = None
    return {
        "message_id": message.get("id"),
        "enrollment_id": enrollment_id,
        "lead_id": lead_id,
        "campaign_id": campaign_id,
        "sequence_id": sequence_id,
        "provider_message_id": message.get("provider_message_id"),
        "provider_thread_id": message.get("provider_thread_id"),
        "correlation_id": message.get("correlation_id"),
        "mailbox": message.get("mailbox"),
    }


def _enrich_from_store(store: Any, workspace_id: str, refs: dict[str, Any]) -> dict[str, Any]:
    out = dict(refs)
    mid = out.get("message_id")
    if not mid:
        return out
    message = store.get_message(workspace_id, str(mid)) if hasattr(store, "get_message") else None
    if not message:
        return out
    enr_id = message.get("enrollment_id")
    if enr_id and hasattr(store, "get_enrollment"):
        enr = store.get_enrollment(str(enr_id), workspace_id=workspace_id)
        if enr:
            out["enrollment_id"] = enr.get("id")
            out["lead_id"] = enr.get("lead_id")
            out["sequence_id"] = enr.get("sequence_id")
            lead = store.get_lead(workspace_id, str(enr["lead_id"])) if enr.get("lead_id") else None
            if lead:
                out["campaign_id"] = lead.get("campaign_id")
                out["lead_id"] = lead.get("id")
    return out


def _result(
    status: str,
    *,
    message: dict[str, Any] | None = None,
    candidates: list[dict[str, Any]] | None = None,
    reason: str | None = None,
    store: Any | None = None,
    workspace_id: str | None = None,
) -> dict[str, Any]:
    refs: dict[str, Any] = {}
    if message:
        refs = _message_refs(message)
        if store is not None and workspace_id:
            refs = _enrich_from_store(store, workspace_id, refs)
    return {
        "status": status,
        "match_status": status,
        "reason": reason,
        "message_id": refs.get("message_id"),
        "lead_id": refs.get("lead_id"),
        "enrollment_id": refs.get("enrollment_id"),
        "campaign_id": refs.get("campaign_id"),
        "sequence_id": refs.get("sequence_id"),
        "matched_message": message,
        "candidates": candidates or [],
        "refs": refs,
    }


def match_inbound_thread(
    store: Any,
    workspace_id: str,
    inbound: dict[str, Any],
    *,
    recent_days: int = 30,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Match inbound mail to an outbound outreach_messages row (workspace only).

    Order:
      1. provider_thread_id
      2. In-Reply-To / References vs provider_message_id
      3. Correlation / reply token in subject/body
      4. Mailbox + exact sender + recent outbound
      5. Scored fallback → needs_review (ambiguous)
    """
    ws = str(workspace_id or "").strip()
    if not ws:
        return _result(UNMATCHED, reason="missing_workspace")

    thread_id = strip_angle_brackets(inbound.get("thread_id"))
    in_reply_to = strip_angle_brackets(inbound.get("in_reply_to"))
    references = [strip_angle_brackets(r) for r in (inbound.get("references") or []) if strip_angle_brackets(r)]
    from_address = str(inbound.get("from_address") or "").strip().lower()
    mailbox = str(inbound.get("mailbox") or "").strip().lower()
    subject = str(inbound.get("subject") or "")
    body = str(inbound.get("text_body") or inbound.get("body") or "")

    # 1) provider_thread_id
    if thread_id and hasattr(store, "find_messages_by_provider_thread_id"):
        rows = store.find_messages_by_provider_thread_id(ws, thread_id)
        if len(rows) == 1:
            return _result(MATCHED, message=rows[0], reason="provider_thread_id", store=store, workspace_id=ws)
        if len(rows) > 1:
            return _result(
                AMBIGUOUS,
                candidates=rows,
                reason="multiple_thread_matches",
                store=store,
                workspace_id=ws,
            )

    # 2) In-Reply-To / References tokens vs provider_message_id
    tokens: list[str] = []
    for token in ([in_reply_to] if in_reply_to else []) + references:
        if token and token not in tokens:
            tokens.append(token)
    token_hits: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for token in tokens:
        row = store.find_message_by_provider_message_id(ws, token)
        if row and str(row.get("id")) not in seen_ids:
            seen_ids.add(str(row["id"]))
            token_hits.append(row)
    if len(token_hits) == 1:
        return _result(MATCHED, message=token_hits[0], reason="in_reply_to_or_references", store=store, workspace_id=ws)
    if len(token_hits) > 1:
        return _result(
            AMBIGUOUS,
            candidates=token_hits,
            reason="multiple_reference_matches",
            store=store,
            workspace_id=ws,
        )

    # 3) Correlation / reply token
    corr_tokens = extract_correlation_tokens(subject, body)
    corr_hits: list[dict[str, Any]] = []
    if corr_tokens and hasattr(store, "find_messages_by_correlation_id"):
        for token in corr_tokens:
            rows = store.find_messages_by_correlation_id(ws, token)
            for row in rows:
                if str(row.get("id")) not in seen_ids:
                    seen_ids.add(str(row["id"]))
                    corr_hits.append(row)
    elif corr_tokens:
        # Fallback: scan recent messages for correlation_id / idempotency containing token
        for token in corr_tokens:
            rows = store._fetchall(
                """
                SELECT * FROM outreach_messages
                WHERE workspace_id = ?
                  AND (
                    lower(COALESCE(correlation_id, '')) = ?
                    OR lower(COALESCE(correlation_id, '')) LIKE ?
                    OR lower(COALESCE(idempotency_key, '')) LIKE ?
                  )
                ORDER BY created_at DESC LIMIT 5
                """,
                (ws, token.lower(), f"%{token.lower()}%", f"%{token.lower()}%"),
            )
            for row in rows:
                if str(row.get("id")) not in seen_ids:
                    seen_ids.add(str(row["id"]))
                    corr_hits.append(row)
    if len(corr_hits) == 1:
        return _result(MATCHED, message=corr_hits[0], reason="correlation_token", store=store, workspace_id=ws)
    if len(corr_hits) > 1:
        return _result(
            AMBIGUOUS,
            candidates=corr_hits,
            reason="multiple_correlation_matches",
            store=store,
            workspace_id=ws,
        )

    # 4) Mailbox + exact sender + recent outbound
    now_dt = now or _utcnow()
    cutoff = (now_dt - timedelta(days=int(recent_days))).replace(microsecond=0).isoformat()
    recent_hits: list[dict[str, Any]] = []
    if from_address:
        recent_hits = store.find_recent_outbound_to_address(
            ws,
            from_address,
            mailbox=mailbox or None,
            since_iso=cutoff,
            limit=10,
        )
    if len(recent_hits) == 1:
        return _result(MATCHED, message=recent_hits[0], reason="mailbox_sender_recent", store=store, workspace_id=ws)
    if len(recent_hits) > 1:
        # Same lead/enrollment → treat as matched to newest; else ambiguous
        lead_ids = set()
        for row in recent_hits:
            enr = store.get_enrollment(str(row.get("enrollment_id") or ""), workspace_id=ws)
            if enr:
                lead_ids.add(str(enr.get("lead_id")))
        if len(lead_ids) == 1:
            return _result(
                MATCHED,
                message=recent_hits[0],
                reason="mailbox_sender_recent_same_lead",
                store=store,
                workspace_id=ws,
            )
        return _result(
            AMBIGUOUS,
            candidates=recent_hits,
            reason="multiple_recent_sender_matches",
            store=store,
            workspace_id=ws,
        )

    # 5) Scored fallback (weak signals → needs_review)
    scored: list[tuple[float, dict[str, Any]]] = []
    if from_address:
        # Leads with same email + any outbound
        lead = store.find_lead_by_email(ws, from_address)
        if lead:
            for enr in store.active_enrollments_for_lead(str(lead["id"]), workspace_id=ws) or []:
                msgs = store._fetchall(
                    """
                    SELECT * FROM outreach_messages
                    WHERE workspace_id = ? AND enrollment_id = ?
                    ORDER BY created_at DESC LIMIT 3
                    """,
                    (ws, str(enr["id"])),
                )
                for msg in msgs:
                    score = 0.4
                    if mailbox and str(msg.get("mailbox") or "").lower() == mailbox:
                        score += 0.2
                    scored.append((score, msg))
            # Also include completed enrollments' recent messages
            all_enr = store._fetchall(
                "SELECT * FROM outreach_enrollments WHERE lead_id = ? AND workspace_id = ?",
                (str(lead["id"]), ws),
            )
            for enr in all_enr:
                msgs = store._fetchall(
                    """
                    SELECT * FROM outreach_messages
                    WHERE workspace_id = ? AND enrollment_id = ?
                      AND sent_at IS NOT NULL AND sent_at >= ?
                    ORDER BY created_at DESC LIMIT 2
                    """,
                    (ws, str(enr["id"]), cutoff),
                )
                for msg in msgs:
                    if any(str(m.get("id")) == str(msg.get("id")) for _, m in scored):
                        continue
                    scored.append((0.35, msg))

    if not scored:
        return _result(UNMATCHED, reason="no_candidates")

    scored.sort(key=lambda x: x[0], reverse=True)
    top_score = scored[0][0]
    top = [m for s, m in scored if s >= top_score - 0.05]
    if len(top) == 1 and top_score >= 0.75:
        return _result(MATCHED, message=top[0], reason="scored_fallback", store=store, workspace_id=ws)
    # Ambiguous / needs review; do not auto-apply
    return _result(
        AMBIGUOUS,
        candidates=[m for _, m in scored[:5]],
        reason="scored_fallback_ambiguous",
        store=store,
        workspace_id=ws,
    )
