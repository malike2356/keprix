"""Normalize ESP webhook events and apply delivery / suppression updates."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any

from keprix.outreach.delivery import next_delivery_state

logger = logging.getLogger(__name__)

# Contract event types
CONTRACT_EVENTS = frozenset(
    {
        "accepted",
        "sent",
        "delivered",
        "deferred",
        "soft_bounce",
        "hard_bounce",
        "complaint",
        "unsubscribe",
        "opened",
        "clicked",
        "failed",
    }
)

_EVENT_TO_DELIVERY_STATE = {
    "accepted": "accepted",
    "sent": "sent",
    "delivered": "delivered",
    "deferred": "deferred",
    "soft_bounce": "soft_bounce",
    "hard_bounce": "hard_bounce",
    "complaint": "complaint",
    "unsubscribe": "unsubscribed",
    "failed": "failed",
    # opened/clicked do not change delivery_state primary; timestamps only
}


def _utcnow() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def normalize_sendgrid_events(payload: Any) -> list[dict[str, Any]]:
    events = payload if isinstance(payload, list) else [payload]
    out: list[dict[str, Any]] = []
    for raw in events:
        if not isinstance(raw, dict):
            continue
        et = str(raw.get("event") or "").lower()
        mapping = {
            "processed": "accepted",
            "deferred": "deferred",
            "delivered": "delivered",
            "bounce": "hard_bounce" if str(raw.get("type") or "").lower() == "bounce" else "soft_bounce",
            "blocked": "hard_bounce",
            "dropped": "failed",
            "spamreport": "complaint",
            "unsubscribe": "unsubscribe",
            "group_unsubscribe": "unsubscribe",
            "open": "opened",
            "click": "clicked",
        }
        if et == "bounce":
            # SendGrid: type=bounce is hard; type=blocked separate; soft via bounce_classification
            btype = str(raw.get("type") or "bounce").lower()
            if btype == "blocked" or str(raw.get("bounce_classification") or "").lower() in (
                "invalid",
                "reputation",
            ):
                contract = "hard_bounce"
            elif btype == "bounce":
                contract = "hard_bounce"
            else:
                contract = "soft_bounce"
        else:
            contract = mapping.get(et)
        if not contract:
            continue
        mid = str(raw.get("sg_message_id") or raw.get("smtp-id") or raw.get("message_id") or "").strip()
        if mid and "." in mid and not mid.startswith("<"):
            # SendGrid often appends .filter...
            mid = mid.split(".")[0]
        idem = str(raw.get("sg_event_id") or raw.get("sg_message_id") or "") or hashlib.sha256(
            json.dumps(raw, sort_keys=True, default=str).encode()
        ).hexdigest()
        out.append(
            {
                "provider": "sendgrid",
                "event_type": contract,
                "provider_message_id": mid or None,
                "idempotency_key": f"sendgrid:{idem}",
                "email": str(raw.get("email") or "").lower() or None,
                "payload": raw,
            }
        )
    return out


def normalize_mailgun_events(payload: Any) -> list[dict[str, Any]]:
    raw = payload
    if isinstance(payload, dict) and "event-data" in payload:
        raw = payload["event-data"]
    if not isinstance(raw, dict):
        return []
    et = str(raw.get("event") or "").lower()
    mapping = {
        "accepted": "accepted",
        "rejected": "failed",
        "delivered": "delivered",
        "failed": "failed",
        "opened": "opened",
        "clicked": "clicked",
        "unsubscribed": "unsubscribe",
        "complained": "complaint",
        "stored": "accepted",
    }
    contract = mapping.get(et)
    severity = str((raw.get("severity") or {}).get("severity") or raw.get("severity") or "").lower()
    reason = str((raw.get("reason") or "")).lower()
    if et == "failed":
        if severity == "permanent" or "bounce" in reason:
            contract = "hard_bounce"
        else:
            contract = "soft_bounce"
    if not contract:
        return []
    msg = raw.get("message") if isinstance(raw.get("message"), dict) else {}
    headers = msg.get("headers") if isinstance(msg.get("headers"), dict) else {}
    mid = str(
        raw.get("message-id")
        or headers.get("message-id")
        or (raw.get("storage") or {}).get("key")
        or ""
    ).strip("<>")
    idem = str(raw.get("id") or "") or hashlib.sha256(
        json.dumps(raw, sort_keys=True, default=str).encode()
    ).hexdigest()
    recipient = str(raw.get("recipient") or "").lower() or None
    return [
        {
            "provider": "mailgun",
            "event_type": contract,
            "provider_message_id": mid or None,
            "idempotency_key": f"mailgun:{idem}",
            "email": recipient,
            "payload": raw,
        }
    ]


def normalize_ses_events(payload: Any) -> list[dict[str, Any]]:
    """Accept SNS envelope or bare SES notification JSON."""
    data = payload
    if isinstance(payload, dict) and payload.get("Type") == "Notification" and payload.get("Message"):
        try:
            data = json.loads(payload["Message"])
        except Exception:
            data = payload
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except Exception:
            return []
    if not isinstance(data, dict):
        return []
    ntype = str(data.get("notificationType") or data.get("eventType") or "").lower()
    mail = data.get("mail") if isinstance(data.get("mail"), dict) else {}
    mid = str(mail.get("messageId") or data.get("mail", {}).get("messageId") or "").strip()
    recipients: list[str] = []
    destination = mail.get("destination") or []
    if isinstance(destination, list):
        recipients = [str(x).lower() for x in destination]

    contract = None
    if ntype in ("delivery", "deliverydelay"):
        contract = "delivered" if ntype == "delivery" else "deferred"
    elif ntype == "bounce":
        bounce = data.get("bounce") if isinstance(data.get("bounce"), dict) else {}
        btype = str(bounce.get("bounceType") or "").lower()
        contract = "hard_bounce" if btype == "permanent" else "soft_bounce"
        for br in bounce.get("bouncedRecipients") or []:
            if isinstance(br, dict) and br.get("emailAddress"):
                recipients.append(str(br["emailAddress"]).lower())
    elif ntype == "complaint":
        contract = "complaint"
        for cr in (data.get("complaint") or {}).get("complainedRecipients") or []:
            if isinstance(cr, dict) and cr.get("emailAddress"):
                recipients.append(str(cr["emailAddress"]).lower())
    elif ntype in ("reject", "reject"):
        contract = "failed"
    elif ntype in ("send",):
        contract = "sent"
    elif ntype in ("open",):
        contract = "opened"
    elif ntype in ("click",):
        contract = "clicked"
    elif ntype in ("subscription",):
        contract = "unsubscribe"
    if not contract:
        return []

    idem_src = mid + ":" + ntype + ":" + ",".join(sorted(set(recipients)))
    idem = hashlib.sha256(idem_src.encode()).hexdigest()
    email = recipients[0] if recipients else None
    return [
        {
            "provider": "ses",
            "event_type": contract,
            "provider_message_id": mid or None,
            "idempotency_key": f"ses:{idem}",
            "email": email,
            "payload": data,
        }
    ]


def normalize_provider_events(provider: str, payload: Any) -> list[dict[str, Any]]:
    p = str(provider or "").lower().strip()
    if p in ("sendgrid", "sg"):
        return normalize_sendgrid_events(payload)
    if p in ("mailgun", "mg"):
        return normalize_mailgun_events(payload)
    if p in ("ses", "aws", "sns"):
        return normalize_ses_events(payload)
    raise ValueError(f"unsupported_provider:{provider}")


def verify_sendgrid_signature(
    *,
    body: bytes,
    signature: str | None,
    timestamp: str | None,
    public_key_pem: str | None = None,
) -> bool:
    """Verify SendGrid signed event webhook when key configured.

    When SENDGRID_WEBHOOK_VERIFY_KEY is unset, returns True (verification skipped).
    """
    key = (public_key_pem or os.environ.get("SENDGRID_WEBHOOK_VERIFY_KEY") or "").strip()
    if not key:
        return True
    if not signature or not timestamp:
        return False
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
        from cryptography.hazmat.primitives.serialization import load_pem_public_key
        import base64

        pem = key if "BEGIN" in key else f"-----BEGIN PUBLIC KEY-----\n{key}\n-----END PUBLIC KEY-----"
        pub = load_pem_public_key(pem.encode())
        if not isinstance(pub, Ed25519PublicKey):
            return False
        pub.verify(base64.b64decode(signature), timestamp.encode() + body)
        return True
    except Exception:
        logger.warning("sendgrid webhook signature verification failed")
        return False


def verify_mailgun_signature(
    *,
    timestamp: str | None,
    token: str | None,
    signature: str | None,
    signing_key: str | None = None,
) -> bool:
    key = (signing_key or os.environ.get("MAILGUN_WEBHOOK_SIGNING_KEY") or "").strip()
    if not key:
        return True
    if not timestamp or not token or not signature:
        return False
    digest = hmac.new(
        key.encode(),
        f"{timestamp}{token}".encode(),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(digest, signature)


def verify_ses_sns(*, payload: dict[str, Any], topic_arn: str | None = None) -> bool:
    """Best-effort SNS topic ARN check when AWS_SNS_TOPIC_ARN is set."""
    expected = (topic_arn or os.environ.get("AWS_SNS_TOPIC_ARN") or "").strip()
    if not expected:
        return True
    got = str(payload.get("TopicArn") or "").strip()
    return got == expected


def verify_provider_signature(provider: str, *, headers: dict[str, str], body: bytes, payload: Any) -> bool:
    p = str(provider or "").lower()
    hdrs = {str(k).lower(): v for k, v in (headers or {}).items()}
    if p == "sendgrid":
        return verify_sendgrid_signature(
            body=body,
            signature=hdrs.get("x-twilio-email-event-webhook-signature"),
            timestamp=hdrs.get("x-twilio-email-event-webhook-timestamp"),
        )
    if p == "mailgun":
        sig_block = {}
        if isinstance(payload, dict):
            sig_block = payload.get("signature") if isinstance(payload.get("signature"), dict) else payload
        return verify_mailgun_signature(
            timestamp=str(sig_block.get("timestamp") or "") or None,
            token=str(sig_block.get("token") or "") or None,
            signature=str(sig_block.get("signature") or "") or None,
        )
    if p in ("ses", "sns"):
        data = payload if isinstance(payload, dict) else {}
        return verify_ses_sns(payload=data)
    return True


def _tracking_allowed(control: dict[str, Any] | None, event_type: str) -> bool:
    if event_type not in ("opened", "clicked"):
        return True
    control = control or {}
    settings = control.get("settings") if isinstance(control.get("settings"), dict) else {}
    if not settings and control.get("settings_json"):
        try:
            settings = json.loads(control["settings_json"] or "{}")
        except Exception:
            settings = {}
    if event_type == "opened":
        return bool(
            control.get("allow_open_tracking")
            or settings.get("allow_open_tracking")
            or settings.get("tracking_opens")
        )
    return bool(
        control.get("allow_click_tracking")
        or settings.get("allow_click_tracking")
        or settings.get("tracking_clicks")
    )


def apply_provider_event(
    workspace_id: str,
    event: dict[str, Any],
    *,
    signature_ok: bool = True,
    store=None,
    ops=None,
    crm_store=None,
) -> dict[str, Any]:
    """Persist + apply one normalized event. Idempotent on (workspace_id, idempotency_key)."""
    from keprix.outreach.ops import get_outreach_ops_store
    from keprix.outreach.store import get_outreach_store

    store = store or get_outreach_store()
    ops = ops or get_outreach_ops_store()
    ws = str(workspace_id or "").strip()
    if not ws:
        raise ValueError("workspace_id is required")
    if not signature_ok:
        return {"ok": False, "reason": "invalid_signature"}

    event_type = str(event.get("event_type") or "")
    if event_type not in CONTRACT_EVENTS:
        return {"ok": False, "reason": "unknown_event_type", "event_type": event_type}

    idem = str(event.get("idempotency_key") or "").strip()
    if not idem:
        idem = f"{event.get('provider')}:{uuid.uuid4().hex}"

    existing = store.get_provider_event_by_idempotency(ws, idem)
    if existing and existing.get("applied_at"):
        return {"ok": True, "duplicate": True, "event": existing}

    control = ops.get_control(ws)
    if event_type in ("opened", "clicked") and not _tracking_allowed(control, event_type):
        row = store.record_provider_event(
            workspace_id=ws,
            provider=str(event.get("provider") or ""),
            event_type=event_type,
            idempotency_key=idem,
            provider_message_id=event.get("provider_message_id"),
            message_id=None,
            payload=event.get("payload") or event,
            signature_ok=signature_ok,
            applied_at=_utcnow(),
        )
        return {"ok": True, "ignored": True, "reason": "tracking_disabled", "event": row}

    message = None
    pmid = event.get("provider_message_id")
    if pmid:
        message = store.find_message_by_provider_message_id(ws, str(pmid))
    if not message and event.get("message_id"):
        message = store.get_message(ws, str(event["message_id"]))

    now = _utcnow()
    message_id = (message or {}).get("id")
    row = store.record_provider_event(
        workspace_id=ws,
        provider=str(event.get("provider") or ""),
        event_type=event_type,
        idempotency_key=idem,
        provider_message_id=pmid,
        message_id=message_id,
        payload=event.get("payload") or event,
        signature_ok=signature_ok,
        applied_at=None,
    )

    updates: dict[str, Any] = {"last_provider_event_at": now}
    delivery_target = _EVENT_TO_DELIVERY_STATE.get(event_type)
    if message and delivery_target:
        new_state = next_delivery_state(message.get("delivery_state"), delivery_target)
        updates["delivery_state"] = new_state
        if event_type == "delivered":
            updates["delivered_at"] = message.get("delivered_at") or now
        if event_type in ("hard_bounce", "soft_bounce"):
            updates["bounced"] = 1
        if event_type == "failed" and not delivery_target:
            updates["send_error"] = "provider_failed"
        store.update_message(ws, str(message["id"]), **updates)
    elif message and event_type == "opened":
        store.update_message(ws, str(message["id"]), opened_at=message.get("opened_at") or now, last_provider_event_at=now)
    elif message and event_type == "clicked":
        store.update_message(ws, str(message["id"]), clicked_at=message.get("clicked_at") or now, last_provider_event_at=now)

    # Suppression + stop enrollments on hard outcomes
    email = str(event.get("email") or "").strip().lower()
    if not email and message:
        # try lead email via enrollment
        try:
            enr = store.get_enrollment(str(message.get("enrollment_id") or ""), workspace_id=ws)
            if enr:
                lead = store.get_lead(ws, str(enr["lead_id"]))
                email = str((lead or {}).get("email") or "").lower()
        except Exception:
            pass

    if event_type in ("hard_bounce", "complaint", "unsubscribe") and email:
        try:
            cstore = crm_store
            if cstore is None:
                from keprix.crm.store import get_crm_store

                cstore = get_crm_store()
            reason = {
                "hard_bounce": "provider_hard_bounce",
                "complaint": "provider_complaint",
                "unsubscribe": "provider_unsubscribe",
            }[event_type]
            cstore.create_suppression_entry(
                ws,
                channel="email",
                address=email,
                reason=reason,
                source=f"outreach_provider:{event.get('provider')}",
                actor_type="system",
                actor_id="outreach_provider_events",
            )
        except Exception:
            logger.exception("failed to create suppression for %s", email)
        try:
            # Stop active / awaiting enrollments for this lead email
            leads = store.list_leads(ws, limit=500)
            for lead in leads:
                if str(lead.get("email") or "").lower() != email:
                    continue
                store.update_lead_status(
                    ws,
                    str(lead["id"]),
                    "unsubscribed" if event_type == "unsubscribe" else lead.get("status") or "lost",
                )
                for enr in store.active_enrollments_for_lead(str(lead["id"]), workspace_id=ws):
                    store.update_enrollment(
                        str(enr["id"]),
                        status="stopped_suppressed" if event_type != "unsubscribe" else "stopped_unsubscribe",
                        next_run_at=None,
                        locked_until=None,
                        locked_by=None,
                        last_error=f"provider_{event_type}",
                    )
                # also stop awaiting_approval
                awaiting = store._fetchall(
                    """
                    SELECT * FROM outreach_enrollments
                    WHERE lead_id = ? AND workspace_id = ? AND status = 'awaiting_approval'
                    """,
                    (str(lead["id"]), ws),
                )
                for enr in awaiting:
                    store.update_enrollment(
                        str(enr["id"]),
                        status="stopped_suppressed" if event_type != "unsubscribe" else "stopped_unsubscribe",
                        next_run_at=None,
                        last_error=f"provider_{event_type}",
                    )
        except Exception:
            logger.exception("failed to stop enrollments for %s", email)

    store.mark_provider_event_applied(ws, str(row["id"]), applied_at=now)
    refreshed = store.get_provider_event(ws, str(row["id"]))
    return {"ok": True, "event": refreshed, "message_id": message_id, "event_type": event_type}


def ingest_provider_webhook(
    workspace_id: str,
    provider: str,
    *,
    payload: Any,
    headers: dict[str, str] | None = None,
    body: bytes | None = None,
    store=None,
) -> dict[str, Any]:
    headers = headers or {}
    raw = body if body is not None else json.dumps(payload, default=str).encode()
    signature_ok = verify_provider_signature(provider, headers=headers, body=raw, payload=payload)
    if not signature_ok:
        return {"ok": False, "reason": "invalid_signature", "applied": 0}

    events = normalize_provider_events(provider, payload)
    results = []
    for ev in events:
        results.append(apply_provider_event(workspace_id, ev, signature_ok=True, store=store))
    return {
        "ok": True,
        "provider": provider,
        "applied": sum(1 for r in results if r.get("ok") and not r.get("duplicate")),
        "duplicates": sum(1 for r in results if r.get("duplicate")),
        "ignored": sum(1 for r in results if r.get("ignored")),
        "results": results,
    }
