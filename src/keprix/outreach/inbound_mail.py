"""Inbound mailbox normalization for outreach replies (Prompt 626).

Adapters (IMAP poll, optional webhook body) share one normalize() shape.
Attachment payloads are never retained; metadata only.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
from datetime import datetime, timezone
from pathlib import PurePosixPath
from typing import Any, Callable

logger = logging.getLogger(__name__)

# Metadata-only defaults
MAX_ATTACHMENT_BYTES = int(os.environ.get("KEPRIX_OUTREACH_INBOUND_MAX_ATTACH_BYTES", str(10 * 1024 * 1024)))
UNSAFE_ATTACHMENT_EXTENSIONS = frozenset(
    {
        ".exe",
        ".bat",
        ".cmd",
        ".com",
        ".scr",
        ".msi",
        ".dll",
        ".ps1",
        ".vbs",
        ".js",
        ".jse",
        ".wsf",
        ".sh",
        ".bash",
        ".zsh",
        ".apk",
        ".jar",
        ".hta",
        ".cpl",
        ".msc",
    }
)
UNSAFE_CONTENT_TYPES = frozenset(
    {
        "application/x-msdownload",
        "application/x-msdos-program",
        "application/x-executable",
        "application/javascript",
        "text/javascript",
        "application/x-sh",
        "application/x-bat",
    }
)

_MESSAGE_ID_RE = re.compile(r"<([^>]+)>|(\S+)")


def strip_angle_brackets(value: str | None) -> str:
    raw = str(value or "").strip()
    if raw.startswith("<") and raw.endswith(">"):
        return raw[1:-1].strip()
    return raw


def parse_references(raw: str | None) -> list[str]:
    """Split a References header into Message-ID tokens (no angle brackets)."""
    if not raw:
        return []
    tokens: list[str] = []
    for match in _MESSAGE_ID_RE.finditer(str(raw)):
        token = strip_angle_brackets(match.group(1) or match.group(2) or "")
        if token and token not in tokens:
            tokens.append(token)
    return tokens


def sanitize_attachment_filename(name: str | None) -> str:
    raw = str(name or "attachment").strip() or "attachment"
    # Drop path components; block traversal
    base = PurePosixPath(raw.replace("\\", "/")).name
    base = base.replace("\x00", "")
    if base in ("", ".", ".."):
        return "attachment"
    return base[:255]


def attachment_meta_safe(
    *,
    filename: str | None,
    size: int | None = None,
    content_type: str | None = None,
) -> dict[str, Any] | None:
    """Return sanitized metadata or None when the attachment is rejected."""
    safe_name = sanitize_attachment_filename(filename)
    ext = ("." + safe_name.rsplit(".", 1)[-1].lower()) if "." in safe_name else ""
    ctype = str(content_type or "").split(";", 1)[0].strip().lower()
    size_i = int(size or 0)
    rejected: list[str] = []
    if ext in UNSAFE_ATTACHMENT_EXTENSIONS:
        rejected.append("unsafe_extension")
    if ctype in UNSAFE_CONTENT_TYPES:
        rejected.append("unsafe_content_type")
    if size_i > MAX_ATTACHMENT_BYTES:
        rejected.append("size_limit")
    if rejected:
        return {
            "filename": safe_name,
            "size": size_i,
            "content_type": ctype or None,
            "rejected": True,
            "reject_reasons": rejected,
        }
    return {
        "filename": safe_name,
        "size": size_i,
        "content_type": ctype or None,
        "rejected": False,
    }


def extract_attachment_meta_from_email_message(msg: Any) -> list[dict[str, Any]]:
    """Walk an email.message.Message and collect attachment metadata only."""
    out: list[dict[str, Any]] = []
    if not getattr(msg, "is_multipart", lambda: False)():
        return out
    for part in msg.walk():
        if part.is_multipart():
            continue
        cd = str(part.get("Content-Disposition", "") or "")
        if "attachment" not in cd.lower() and not part.get_filename():
            continue
        filename = part.get_filename()
        payload = part.get_payload(decode=True)
        size = len(payload) if isinstance(payload, (bytes, bytearray)) else 0
        meta = attachment_meta_safe(
            filename=filename,
            size=size,
            content_type=part.get_content_type(),
        )
        if meta:
            out.append(meta)
    return out


def _stable_checksum_payload(fields: dict[str, Any]) -> str:
    stable = {
        "workspace_id": fields.get("workspace_id"),
        "mailbox": fields.get("mailbox"),
        "provider_message_id": fields.get("provider_message_id"),
        "thread_id": fields.get("thread_id"),
        "in_reply_to": fields.get("in_reply_to"),
        "references": fields.get("references") or [],
        "from_address": fields.get("from_address"),
        "to_addresses": fields.get("to_addresses") or [],
        "subject": fields.get("subject"),
        "text_body": fields.get("text_body"),
        "received_at": fields.get("received_at"),
        "attachments_meta": fields.get("attachments_meta") or [],
    }
    blob = json.dumps(stable, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def normalize_inbound(
    *,
    workspace_id: str,
    mailbox: str | None = None,
    provider_message_id: str | None = None,
    thread_id: str | None = None,
    in_reply_to: str | None = None,
    references: list[str] | str | None = None,
    from_address: str | None = None,
    to_addresses: list[str] | None = None,
    subject: str | None = None,
    text_body: str | None = None,
    received_at: str | datetime | None = None,
    attachments_meta: list[dict[str, Any]] | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Normalize a provider/IMAP/webhook payload into the shared inbound shape."""
    refs: list[str]
    if isinstance(references, str):
        refs = parse_references(references)
    else:
        refs = [strip_angle_brackets(r) for r in (references or []) if strip_angle_brackets(r)]

    recv: str
    if isinstance(received_at, datetime):
        recv = received_at.astimezone(timezone.utc).replace(microsecond=0).isoformat()
    elif received_at:
        recv = str(received_at)
    else:
        recv = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    safe_meta: list[dict[str, Any]] = []
    for item in attachments_meta or []:
        meta = attachment_meta_safe(
            filename=item.get("filename") or item.get("name"),
            size=item.get("size"),
            content_type=item.get("content_type") or item.get("contentType"),
        )
        if meta:
            safe_meta.append(meta)
        # Never copy raw / data / payload keys

    fields: dict[str, Any] = {
        "workspace_id": str(workspace_id or "").strip(),
        "mailbox": str(mailbox or "").strip().lower() or None,
        "provider_message_id": strip_angle_brackets(provider_message_id) or None,
        "thread_id": strip_angle_brackets(thread_id) or None,
        "in_reply_to": strip_angle_brackets(in_reply_to) or None,
        "references": refs,
        "from_address": str(from_address or "").strip().lower(),
        "to_addresses": [str(a).strip().lower() for a in (to_addresses or []) if str(a).strip()],
        "subject": str(subject or ""),
        "text_body": str(text_body or ""),
        "received_at": recv,
        "attachments_meta": safe_meta,
    }
    fields["payload_checksum"] = _stable_checksum_payload(fields)
    if extra:
        # Non-canonical hints (uid, folder, account_id) for cursor advance only
        fields["_meta"] = {k: v for k, v in extra.items() if k not in ("raw", "payload", "data", "body_bytes")}
    return fields


def normalize_from_parsed_imap(
    workspace_id: str,
    parsed: dict[str, Any],
    *,
    mailbox: str | None = None,
    account_id: str | None = None,
) -> dict[str, Any]:
    """Adapt email.helpers.parse_message output (+ In-Reply-To/References)."""
    return normalize_inbound(
        workspace_id=workspace_id,
        mailbox=mailbox or parsed.get("mailbox"),
        provider_message_id=parsed.get("message_id") or parsed.get("provider_message_id"),
        thread_id=parsed.get("thread_id"),
        in_reply_to=parsed.get("in_reply_to"),
        references=parsed.get("references"),
        from_address=parsed.get("from_address"),
        to_addresses=list(parsed.get("to_addresses") or []),
        subject=parsed.get("subject"),
        text_body=parsed.get("body_text") or parsed.get("text_body") or "",
        received_at=parsed.get("received_at"),
        attachments_meta=parsed.get("attachments_meta") or [],
        extra={
            "uid": parsed.get("uid"),
            "folder": parsed.get("folder"),
            "account_id": account_id,
            "source": "imap",
        },
    )


def normalize_from_webhook_body(workspace_id: str, body: dict[str, Any]) -> dict[str, Any]:
    """Provider inbound webhook / test helper adapter (same normalize shape)."""
    refs = body.get("references") or body.get("References")
    attachments = body.get("attachments_meta") or body.get("attachments") or []
    # Strip dangerous keys from attachment entries before sanitize
    cleaned_atts: list[dict[str, Any]] = []
    for att in attachments if isinstance(attachments, list) else []:
        if not isinstance(att, dict):
            continue
        cleaned_atts.append(
            {
                "filename": att.get("filename") or att.get("name"),
                "size": att.get("size"),
                "content_type": att.get("content_type") or att.get("contentType"),
            }
        )
    return normalize_inbound(
        workspace_id=workspace_id,
        mailbox=body.get("mailbox") or body.get("to") or (body.get("to_addresses") or [None])[0],
        provider_message_id=body.get("provider_message_id") or body.get("message_id") or body.get("Message-ID"),
        thread_id=body.get("thread_id") or body.get("threadId"),
        in_reply_to=body.get("in_reply_to") or body.get("inReplyTo") or body.get("In-Reply-To"),
        references=refs,
        from_address=body.get("from_address") or body.get("from") or body.get("from_email"),
        to_addresses=body.get("to_addresses") or body.get("toAddresses") or ([body["to"]] if body.get("to") else []),
        subject=body.get("subject"),
        text_body=body.get("text_body") or body.get("body") or body.get("text") or "",
        received_at=body.get("received_at") or body.get("receivedAt"),
        attachments_meta=cleaned_atts,
        extra={"source": body.get("source") or "webhook", "account_id": body.get("account_id")},
    )


def fetch_imap_since_uid(
    account: dict[str, Any],
    *,
    folder: str = "INBOX",
    since_uid: int | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Fetch IMAP messages with UID greater than since_uid (inclusive gap-safe)."""
    from keprix.email.helpers import fetch_new_messages, imap_session, parse_message, quote_mailbox

    # Prefer cursor-aware fetch when since_uid is set
    if since_uid is None or int(since_uid) <= 0:
        messages = fetch_new_messages(account, folder=folder)
        return messages[-limit:]

    from keprix.email.crypto import decrypt_secret

    password = account.get("password")
    if password is None and account.get("password_encrypted"):
        password = decrypt_secret(account.get("password_encrypted", ""))
    cfg = {**account, "password": password, "username": account["username"]}
    results: list[dict[str, Any]] = []
    with imap_session(cfg) as conn:
        conn.select(quote_mailbox(folder), readonly=True)
        # UID SEARCH UID (since+1):*
        criteria = f"{int(since_uid) + 1}:*"
        status, data = conn.uid("SEARCH", None, criteria)
        if status != "OK" or not data or not data[0]:
            return results
        uids = data[0].split()
        for uid_b in uids[-limit:]:
            uid = int(uid_b)
            st, fetched = conn.uid("FETCH", uid_b, "(RFC822)")
            if st != "OK" or not fetched:
                continue
            for item in fetched:
                if not isinstance(item, tuple) or len(item) < 2:
                    continue
                parsed = parse_message(item[1], uid=uid, folder=folder)
                results.append(parsed)
    return results


def resolve_bound_email_accounts(
    workspace_id: str,
    *,
    store: Any,
    ops: Any | None = None,
    load_account: Callable[[str], dict[str, Any] | None] | None = None,
) -> list[dict[str, Any]]:
    """Resolve campaign + control default email accounts for a workspace."""
    from keprix.outreach.delivery import _load_email_account

    loader = load_account or _load_email_account
    account_ids: list[str] = []
    try:
        if ops is not None:
            control = ops.get_control(workspace_id)
            default_id = (control or {}).get("default_email_account_id")
            if default_id:
                account_ids.append(str(default_id))
    except Exception:
        pass
    try:
        campaigns = store.list_campaigns(workspace_id)
        for camp in campaigns:
            aid = camp.get("email_account_id")
            if aid and str(aid) not in account_ids:
                account_ids.append(str(aid))
    except Exception:
        pass

    accounts: list[dict[str, Any]] = []
    seen: set[str] = set()
    for aid in account_ids:
        if aid in seen:
            continue
        seen.add(aid)
        acc = loader(aid)
        if acc:
            acc = dict(acc)
            acc.setdefault("id", aid)
            accounts.append(acc)
    return accounts
