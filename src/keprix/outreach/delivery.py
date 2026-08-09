"""Approved outreach email delivery (SMTP / ESP) + delivery state helpers.

Honesty rules:
- Default KEPRIX_OUTREACH_DRY_RUN=1: never claim live send.
- not_configured when no SMTP bind and no ESP credentials: do not stamp sent_at.
- Soft Wall remains the cold-send gate (callers revalidate before send).
"""

from __future__ import annotations

import logging
import os
import re
import smtplib
import uuid
from datetime import datetime, timezone
from email.utils import make_msgid
from typing import Any

logger = logging.getLogger(__name__)

DELIVERY_STATES: tuple[str, ...] = (
    "draft",
    "queued",
    "accepted",
    "sent",
    "delivered",
    "deferred",
    "soft_bounce",
    "hard_bounce",
    "complaint",
    "unsubscribed",
    "failed",
    "cancelled",
)

# Monotonic rank for normal forward progress. Terminal failure / complaint
# states may override a prior delivered/sent per late-bounce policy.
_STATE_RANK: dict[str, int] = {
    "draft": 0,
    "queued": 1,
    "accepted": 2,
    "sent": 3,
    "deferred": 3,
    "delivered": 4,
    "opened": 5,  # tracking-only alias; not stored as delivery_state primary
    "clicked": 5,
    "soft_bounce": 6,
    "hard_bounce": 7,
    "complaint": 7,
    "unsubscribed": 7,
    "failed": 7,
    "cancelled": 7,
}

_TERMINAL_OVERRIDE = frozenset(
    {"soft_bounce", "hard_bounce", "complaint", "unsubscribed", "failed", "cancelled"}
)

_PLACEHOLDER_RE = re.compile(r"\{\{\s*([a-zA-Z0-9_.]+)\s*\}\}|\{([a-zA-Z0-9_]+)\}")


def _utcnow() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def dry_run_enabled(explicit: bool | None = None) -> bool:
    if explicit is True:
        return True
    if explicit is False:
        return False
    return os.environ.get("KEPRIX_OUTREACH_DRY_RUN", "1") not in ("0", "false", "False")


def can_transition(current: str | None, new_state: str) -> bool:
    """True when new_state may replace current (monotonic + late-bounce policy)."""
    cur = (current or "draft").strip().lower() or "draft"
    nxt = (new_state or "").strip().lower()
    if nxt not in _STATE_RANK and nxt not in DELIVERY_STATES:
        return False
    if cur == nxt:
        return True
    if nxt in _TERMINAL_OVERRIDE:
        # Late bounce / complaint after delivered is allowed.
        return True
    return _STATE_RANK.get(nxt, -1) >= _STATE_RANK.get(cur, -1)


def next_delivery_state(current: str | None, new_state: str) -> str:
    """Return the state to store; keep current when transition is not allowed."""
    cur = (current or "draft").strip().lower() or "draft"
    nxt = (new_state or "").strip().lower()
    if can_transition(cur, nxt):
        return nxt
    return cur


def preview_message(
    template: dict[str, Any] | str,
    lead: dict[str, Any],
    *,
    campaign: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Render subject/body and report missing merge fields."""
    from keprix.outreach.service import _render_template

    if isinstance(template, str):
        subject_tpl = ""
        body_tpl = template
    else:
        subject_tpl = str(template.get("subject") or "")
        body_tpl = str(template.get("body") or "")
        if template.get("cta"):
            body_tpl = f"{body_tpl}\n\n{template['cta']}"
        if template.get("link"):
            body_tpl = f"{body_tpl}\n{template['link']}"

    missing: list[str] = []
    warnings: list[str] = []
    for raw in (subject_tpl, body_tpl):
        for m in _PLACEHOLDER_RE.finditer(raw):
            key = (m.group(1) or m.group(2) or "").split(".")[0]
            if not key:
                continue
            if key in ("booking_link", "campaign"):
                continue
            if key not in lead or lead.get(key) in (None, ""):
                if key not in missing:
                    missing.append(key)

    subject = _render_template(subject_tpl, lead, campaign)
    body = _render_template(body_tpl, lead, campaign)
    if missing:
        warnings.append("missing_merge_fields")
    if not str(lead.get("email") or "").strip():
        warnings.append("lead_missing_email")
        missing.append("email")
    return {
        "subject": subject,
        "body": body,
        "missing_fields": missing,
        "warnings": warnings,
    }


def _esp_available(provider: str) -> bool:
    p = provider.lower()
    if p == "sendgrid":
        return bool(str(os.environ.get("SENDGRID_API_KEY") or "").strip())
    if p == "mailgun":
        return bool(
            str(os.environ.get("MAILGUN_API_KEY") or "").strip()
            and str(os.environ.get("MAILGUN_DOMAIN") or "").strip()
        )
    if p == "ses":
        return bool(
            str(os.environ.get("AWS_ACCESS_KEY_ID") or "").strip()
            and str(os.environ.get("AWS_SECRET_ACCESS_KEY") or "").strip()
            and str(os.environ.get("AWS_SES_REGION") or os.environ.get("AWS_REGION") or "").strip()
        )
    return False


def _load_email_account(account_id: str) -> dict[str, Any] | None:
    """Best-effort sync lookup of a configured email account."""
    aid = str(account_id or "").strip()
    if not aid:
        return None
    try:
        from keprix.email.store import get_email_store

        store = get_email_store()
        for rec in getattr(store, "_accounts", {}).values():
            if str(getattr(rec, "id", "")) == aid:
                return rec.to_connection()
    except Exception:
        pass
    try:
        from keprix.db.session import sync_session_factory

        Session = sync_session_factory()
        if Session is None:
            return None
        from keprix.db.models import EmailAccountRow

        with Session() as session:
            row = session.get(EmailAccountRow, aid)
            if row is None:
                return None
            return {
                "id": row.id,
                "user_id": row.user_id,
                "label": row.label,
                "email_address": row.email_address,
                "imap_host": row.imap_host,
                "imap_port": row.imap_port,
                "smtp_host": row.smtp_host,
                "smtp_port": row.smtp_port,
                "username": row.username,
                "password_encrypted": row.password_encrypted,
                "use_tls": row.use_tls,
                "use_starttls": row.use_starttls,
                "oauth_provider": getattr(row, "oauth_provider", None),
                "oauth_vault_item_id": getattr(row, "oauth_vault_item_id", None),
            }
    except Exception:
        return None


def resolve_sender(
    workspace_id: str,
    campaign: dict[str, Any] | None = None,
    *,
    control: dict[str, Any] | None = None,
    account_override: dict[str, Any] | None = None,
    preferred_provider: str | None = None,
) -> dict[str, Any]:
    """Resolve outbound sender bind.

    Returns dict with keys:
      mode: smtp | sendgrid | mailgun | ses | not_configured | dry_run
      account_id, mailbox, account (smtp), provider, reason
    """
    _ = workspace_id  # reserved for future workspace-scoped vault binds
    if account_override:
        mailbox = str(
            account_override.get("email_address")
            or account_override.get("mailbox")
            or account_override.get("username")
            or ""
        )
        return {
            "mode": "smtp",
            "provider": "smtp",
            "account_id": str(account_override.get("id") or account_override.get("account_id") or ""),
            "mailbox": mailbox,
            "account": account_override,
        }

    control = control or {}
    settings = control.get("settings") if isinstance(control.get("settings"), dict) else {}
    if not settings and control.get("settings_json"):
        try:
            import json

            settings = json.loads(control["settings_json"] or "{}")
        except Exception:
            settings = {}

    account_id = str(
        (campaign or {}).get("email_account_id")
        or control.get("default_email_account_id")
        or settings.get("default_email_account_id")
        or ""
    ).strip()
    if account_id:
        account = _load_email_account(account_id)
        if account and (account.get("smtp_host") or account.get("password_encrypted") or account.get("access_token")):
            mailbox = str(account.get("email_address") or account.get("username") or "")
            return {
                "mode": "smtp",
                "provider": "smtp",
                "account_id": account_id,
                "mailbox": mailbox,
                "account": account,
            }

    pref = (preferred_provider or os.environ.get("KEPRIX_OUTREACH_PROVIDER") or "").strip().lower()
    for candidate in ([pref] if pref else []) + ["sendgrid", "mailgun", "ses"]:
        if not candidate or candidate == "smtp":
            continue
        if _esp_available(candidate):
            mailbox = str(
                os.environ.get("KEPRIX_OUTREACH_FROM_EMAIL")
                or os.environ.get("MAILGUN_FROM")
                or os.environ.get("SENDGRID_FROM")
                or ""
            ).strip()
            return {
                "mode": candidate,
                "provider": candidate,
                "account_id": None,
                "mailbox": mailbox,
                "account": None,
            }

    return {
        "mode": "not_configured",
        "provider": None,
        "account_id": account_id or None,
        "mailbox": None,
        "account": None,
        "reason": "not_configured",
    }


def _send_smtp(
    account: dict[str, Any],
    *,
    to_email: str,
    subject: str,
    body: str,
    mailbox: str | None = None,
) -> dict[str, Any]:
    from keprix.email.helpers import send_smtp_message

    from_addr = str(mailbox or account.get("email_address") or account.get("username") or "")
    if not from_addr:
        raise ValueError("smtp_from_missing")
    result = send_smtp_message(
        account,
        from_addr=from_addr,
        to_addresses=[to_email],
        cc_addresses=[],
        subject=subject,
        body=body,
    )
    if isinstance(result, dict):
        mid = result.get("message_id") or result.get("provider_message_id")
    else:
        mid = None
    if not mid:
        mid = make_msgid(domain=from_addr.split("@")[-1] if "@" in from_addr else "keprix.local")
    return {
        "sent": True,
        "provider": "smtp",
        "provider_message_id": str(mid).strip("<>"),
        "mailbox": from_addr,
    }


def _send_sendgrid(*, to_email: str, subject: str, body: str, mailbox: str) -> dict[str, Any]:
    import httpx

    api_key = str(os.environ.get("SENDGRID_API_KEY") or "").strip()
    if not api_key:
        return {"sent": False, "reason": "not_configured", "provider": "sendgrid"}
    from_email = mailbox or str(os.environ.get("SENDGRID_FROM") or "").strip()
    if not from_email:
        return {"sent": False, "reason": "not_configured", "provider": "sendgrid", "error": "from_missing"}
    payload = {
        "personalizations": [{"to": [{"email": to_email}]}],
        "from": {"email": from_email},
        "subject": subject,
        "content": [{"type": "text/plain", "value": body}],
    }
    resp = httpx.post(
        "https://api.sendgrid.com/v3/mail/send",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json=payload,
        timeout=30.0,
    )
    if resp.status_code >= 500:
        return {"sent": False, "retryable": True, "error": f"sendgrid_http_{resp.status_code}", "provider": "sendgrid"}
    if resp.status_code >= 400:
        return {
            "sent": False,
            "permanent": resp.status_code in (400, 401, 403),
            "error": f"sendgrid_http_{resp.status_code}:{resp.text[:200]}",
            "provider": "sendgrid",
        }
    mid = resp.headers.get("X-Message-Id") or f"sg-{uuid.uuid4().hex}"
    return {"sent": True, "provider": "sendgrid", "provider_message_id": mid, "mailbox": from_email}


def _send_mailgun(*, to_email: str, subject: str, body: str, mailbox: str) -> dict[str, Any]:
    import httpx

    api_key = str(os.environ.get("MAILGUN_API_KEY") or "").strip()
    domain = str(os.environ.get("MAILGUN_DOMAIN") or "").strip()
    if not api_key or not domain:
        return {"sent": False, "reason": "not_configured", "provider": "mailgun"}
    from_email = mailbox or str(os.environ.get("MAILGUN_FROM") or f"noreply@{domain}").strip()
    base = str(os.environ.get("MAILGUN_API_BASE") or "https://api.mailgun.net").rstrip("/")
    resp = httpx.post(
        f"{base}/v3/{domain}/messages",
        auth=("api", api_key),
        data={"from": from_email, "to": to_email, "subject": subject, "text": body},
        timeout=30.0,
    )
    if resp.status_code >= 500:
        return {"sent": False, "retryable": True, "error": f"mailgun_http_{resp.status_code}", "provider": "mailgun"}
    if resp.status_code >= 400:
        return {
            "sent": False,
            "permanent": resp.status_code in (400, 401, 403),
            "error": f"mailgun_http_{resp.status_code}:{resp.text[:200]}",
            "provider": "mailgun",
        }
    data = {}
    try:
        data = resp.json()
    except Exception:
        pass
    mid = str(data.get("id") or f"mg-{uuid.uuid4().hex}").strip("<>")
    return {"sent": True, "provider": "mailgun", "provider_message_id": mid, "mailbox": from_email}


def _send_ses(*, to_email: str, subject: str, body: str, mailbox: str) -> dict[str, Any]:
    region = str(os.environ.get("AWS_SES_REGION") or os.environ.get("AWS_REGION") or "").strip()
    access = str(os.environ.get("AWS_ACCESS_KEY_ID") or "").strip()
    secret = str(os.environ.get("AWS_SECRET_ACCESS_KEY") or "").strip()
    if not (region and access and secret):
        return {"sent": False, "reason": "not_configured", "provider": "ses"}
    from_email = mailbox or str(os.environ.get("AWS_SES_FROM") or os.environ.get("KEPRIX_OUTREACH_FROM_EMAIL") or "").strip()
    if not from_email:
        return {"sent": False, "reason": "not_configured", "provider": "ses", "error": "from_missing"}
    # Minimal SES via boto3 when present; else not_configured (do not claim ready).
    try:
        import boto3  # type: ignore
    except Exception:
        return {
            "sent": False,
            "reason": "not_configured",
            "provider": "ses",
            "error": "boto3_missing",
        }
    try:
        client = boto3.client(
            "sesv2",
            region_name=region,
            aws_access_key_id=access,
            aws_secret_access_key=secret,
        )
        resp = client.send_email(
            FromEmailAddress=from_email,
            Destination={"ToAddresses": [to_email]},
            Content={
                "Simple": {
                    "Subject": {"Data": subject, "Charset": "UTF-8"},
                    "Body": {"Text": {"Data": body, "Charset": "UTF-8"}},
                }
            },
        )
        mid = str(resp.get("MessageId") or f"ses-{uuid.uuid4().hex}")
        return {"sent": True, "provider": "ses", "provider_message_id": mid, "mailbox": from_email}
    except Exception as exc:
        retryable = "Throttl" in type(exc).__name__ or "timeout" in str(exc).lower()
        return {
            "sent": False,
            "retryable": retryable,
            "permanent": not retryable,
            "error": str(exc)[:300],
            "provider": "ses",
        }


def send_approved_message(
    *,
    workspace_id: str,
    to_email: str,
    subject: str,
    body: str,
    campaign: dict[str, Any] | None = None,
    control: dict[str, Any] | None = None,
    idempotency_key: str | None = None,
    dry_run: bool | None = None,
    account_override: dict[str, Any] | None = None,
    existing_message: dict[str, Any] | None = None,
    correlation_id: str | None = None,
) -> dict[str, Any]:
    """Send an approved outreach email. Idempotent by idempotency_key when message already sent."""
    to_addr = str(to_email or "").strip().lower()
    if not to_addr:
        return {"sent": False, "permanent": True, "error": "missing_to", "reason": "missing_to"}

    # Idempotent replay: already accepted/sent+
    if existing_message:
        prior_state = str(existing_message.get("delivery_state") or "")
        if existing_message.get("sent_at") or prior_state in (
            "accepted",
            "sent",
            "delivered",
            "deferred",
            "soft_bounce",
            "hard_bounce",
            "complaint",
            "unsubscribed",
        ):
            return {
                "sent": True,
                "idempotent": True,
                "dry_run": bool(existing_message.get("provider") == "dry_run"),
                "provider": existing_message.get("provider"),
                "provider_message_id": existing_message.get("provider_message_id"),
                "provider_thread_id": existing_message.get("provider_thread_id"),
                "mailbox": existing_message.get("mailbox"),
                "delivery_state": prior_state or "sent",
                "message_id": existing_message.get("id"),
                "to": to_addr,
            }

    if dry_run_enabled(dry_run):
        mid = f"dryrun-{uuid.uuid4().hex}"
        return {
            "sent": True,
            "dry_run": True,
            "provider": "dry_run",
            "provider_message_id": mid,
            "mailbox": None,
            "delivery_state": "sent",
            "to": to_addr,
            "idempotency_key": idempotency_key,
            "correlation_id": correlation_id,
        }

    sender = resolve_sender(
        workspace_id,
        campaign,
        control=control,
        account_override=account_override,
    )
    if sender.get("mode") == "not_configured" or sender.get("reason") == "not_configured":
        return {
            "sent": False,
            "dry_run": False,
            "reason": "not_configured",
            "error": "not_configured",
            "to": to_addr,
            "idempotency_key": idempotency_key,
        }

    mode = str(sender.get("mode") or "")
    mailbox = str(sender.get("mailbox") or "") or None
    try:
        if mode == "smtp":
            account = sender.get("account") or {}
            # Resolve encrypted password / oauth token when needed (sync best-effort).
            if account.get("password_encrypted") and not account.get("password"):
                try:
                    from keprix.email.crypto import decrypt_secret

                    account = {**account, "password": decrypt_secret(account["password_encrypted"])}
                except Exception:
                    pass
            out = _send_smtp(account, to_email=to_addr, subject=subject, body=body, mailbox=mailbox)
        elif mode == "sendgrid":
            out = _send_sendgrid(to_email=to_addr, subject=subject, body=body, mailbox=mailbox or "")
        elif mode == "mailgun":
            out = _send_mailgun(to_email=to_addr, subject=subject, body=body, mailbox=mailbox or "")
        elif mode == "ses":
            out = _send_ses(to_email=to_addr, subject=subject, body=body, mailbox=mailbox or "")
        else:
            return {
                "sent": False,
                "reason": "not_configured",
                "error": f"unknown_mode:{mode}",
                "to": to_addr,
            }
    except smtplib.SMTPServerDisconnected as exc:
        return {"sent": False, "retryable": True, "error": str(exc)[:300], "provider": mode, "to": to_addr}
    except smtplib.SMTPRecipientsRefused as exc:
        return {"sent": False, "permanent": True, "error": str(exc)[:300], "provider": mode, "to": to_addr}
    except smtplib.SMTPAuthenticationError as exc:
        return {"sent": False, "permanent": True, "error": str(exc)[:300], "provider": mode, "to": to_addr}
    except Exception as exc:
        logger.exception("outreach send failed mode=%s to=%s", mode, to_addr)
        return {"sent": False, "retryable": True, "error": str(exc)[:300], "provider": mode, "to": to_addr}

    if out.get("reason") == "not_configured":
        return {**out, "sent": False, "dry_run": False, "to": to_addr, "idempotency_key": idempotency_key}
    if not out.get("sent"):
        return {**out, "to": to_addr, "idempotency_key": idempotency_key}

    return {
        **out,
        "sent": True,
        "dry_run": False,
        "delivery_state": "accepted" if mode != "smtp" else "sent",
        "to": to_addr,
        "account_id": sender.get("account_id"),
        "idempotency_key": idempotency_key,
        "correlation_id": correlation_id,
        "at": _utcnow(),
    }
