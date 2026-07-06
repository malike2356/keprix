"""Outbound review notifications (email + optional webhook)."""

from __future__ import annotations

import hashlib
import hmac
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from keprix.review_gateway.store import ReviewRequest


def _dispatch_log() -> Path:
    try:
        from keprix_cli.config import get_keprix_home

        root = Path(get_keprix_home()) / "review_gateway"
    except Exception:
        root = Path.home() / ".keprix" / "review_gateway"
    root.mkdir(parents=True, exist_ok=True)
    return root / "dispatch.log"


def _sign_webhook(body: bytes, secret: bytes) -> str:
    return hmac.new(secret, body, hashlib.sha256).hexdigest()


def _log_fallback(payload: dict[str, Any]) -> None:
    _dispatch_log().open("a", encoding="utf-8").write(json.dumps(payload) + "\n")


def _audit_domain_pack(req: ReviewRequest) -> str | None:
    if req.domain_pack:
        return req.domain_pack
    from keprix.products.loader import get_default_audit_domain_pack

    return get_default_audit_domain_pack()


async def dispatch_review_notification(
    req: ReviewRequest,
    *,
    review_url: str,
    workspace_name: str = "Keprix",
    reminder: bool = False,
) -> dict[str, Any]:
    expires_at = req.expires_at
    expires_date = expires_at[:10]
    template_name = "review_reminder" if reminder else "review_request"
    try:
        from keprix.notify_external.smtp_sender import send_email

        notification_id = await send_email(
            req.workspace_id,
            req.reviewer_email,
            template_name=template_name,
            template_vars={
                "title": req.title,
                "context_message": req.context_message,
                "review_url": review_url,
                "expires_at": expires_at,
                "expires_date": expires_date,
                "workspace_name": workspace_name,
            },
            triggered_by="review_gateway",
            triggered_by_id=req.id,
        )
        email_result: dict[str, Any] = {"notification_id": notification_id, "sent": True}
    except Exception:
        subject_prefix = "[Reminder] " if reminder else "[Action needed] "
        subject = f"{subject_prefix}{req.title} - review by {expires_date}"
        _log_fallback(
            {
                "event": "review_email",
                "request_id": req.id,
                "to": req.reviewer_email,
                "subject": subject,
                "review_url": review_url,
            }
        )
        email_result = {"sent": False, "fallback_log": True}

    from keprix.governance.audit_events import emit_audit_event

    event_type = "cso_review_reminder_sent" if reminder else "cso_review_assigned"
    await emit_audit_event(
        event_type,
        workspace_id=req.workspace_id,
        actor_type="system",
        summary=f"Review request sent to CSO for '{req.title}'",
        subject_type="review_request",
        subject_id=req.id,
        detail={
            "review_request_id": req.id,
            "reviewer_email_hash": hashlib.sha256(req.reviewer_email.encode("utf-8")).hexdigest(),
            "artifact_title": req.title,
            "token_id": req.token_id,
        },
        severity="notice",
        domain_pack=_audit_domain_pack(req),
    )

    webhook_result: dict[str, Any] | None = None
    if req.reviewer_webhook_url:
        import httpx

        body = {
            "event": "review_requested",
            "review_request_id": req.id,
            "title": req.title,
            "context_message": req.context_message,
            "review_url": review_url,
            "expires_at": req.expires_at,
            "reviewer_name": req.reviewer_name,
        }
        raw = json.dumps(body).encode("utf-8")
        signature = _sign_webhook(raw, b"keprix-review-webhook")
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    req.reviewer_webhook_url,
                    content=raw,
                    headers={
                        "Content-Type": "application/json",
                        "X-Keprix-Signature": signature,
                    },
                )
            webhook_result = {"status_code": response.status_code}
        except Exception as exc:
            webhook_result = {"error": str(exc)}

    return {"email": email_result, "webhook": webhook_result}


async def dispatch_cancellation(req: ReviewRequest) -> None:
    _log_fallback(
        {
            "event": "review_cancelled",
            "request_id": req.id,
            "title": req.title,
            "to": req.reviewer_email,
            "token_id": req.token_id,
        }
    )


async def dispatch_decision_receipt(req: ReviewRequest, action: str, note: str) -> None:
    try:
        from keprix.notify_external.smtp_sender import send_email

        await send_email(
            req.workspace_id,
            req.reviewer_email,
            template_name="review_receipt",
            template_vars={
                "title": req.title,
                "action": action,
                "decided_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                "review_request_id": req.id,
            },
            triggered_by="review_gateway",
            triggered_by_id=req.id,
        )
    except Exception:
        _log_fallback(
            {
                "event": "review_decision_receipt",
                "request_id": req.id,
                "to": req.reviewer_email,
                "action": action,
                "note": note,
            }
        )

    from keprix.governance.audit_events import emit_audit_event

    event_type = {
        "approve": "cso_review_approved",
        "reject": "cso_review_rejected",
        "request_change": "cso_review_change_requested",
    }.get(action, "cso_review_approved")
    await emit_audit_event(
        event_type,
        workspace_id=req.workspace_id,
        actor_type="external_reviewer",
        summary=f"CSO decision recorded for '{req.title}'",
        subject_type="review_request",
        subject_id=req.id,
        detail={
            "review_request_id": req.id,
            "reviewer_name": req.reviewer_name,
            "reviewer_email_hash": hashlib.sha256(req.reviewer_email.encode("utf-8")).hexdigest(),
            "decision": action,
            "note_length": len(note or ""),
            "token_id": req.token_id,
            "artifact_title": req.title,
        },
        severity="notice",
        domain_pack=_audit_domain_pack(req),
    )
