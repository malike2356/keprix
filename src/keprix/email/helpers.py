"""IMAP/SMTP helpers for the email module."""

from __future__ import annotations

import email as email_mod
import email.header
import email.utils
import html
import imaplib
import logging
import os
import re
import smtplib
from contextlib import contextmanager
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

from keprix.email.crypto import decrypt_secret

logger = logging.getLogger(__name__)

IMAP_TIMEOUT = int(os.environ.get("EMAIL_SOCKET_TIMEOUT", "30"))


def quote_mailbox(name: str) -> str:
    return '"' + (name or "").replace("\\", "\\\\").replace('"', '\\"') + '"'


def decode_header_value(raw: str | None) -> str:
    if not raw:
        return ""
    try:
        return str(email.header.make_header(email.header.decode_header(raw)))
    except Exception:
        parts: list[str] = []
        for data, charset in email.header.decode_header(raw):
            if isinstance(data, bytes):
                try:
                    parts.append(data.decode(charset or "utf-8", errors="replace"))
                except (LookupError, ValueError):
                    parts.append(data.decode("utf-8", errors="replace"))
            else:
                parts.append(str(data))
        return "".join(parts)


def smtp_security_mode(port: int, use_starttls: bool) -> str:
    if use_starttls:
        return "starttls"
    if port == 587:
        return "starttls"
    if port == 465:
        return "ssl"
    return "plain"


def open_imap_connection(
    host: str,
    port: int,
    *,
    use_tls: bool,
    use_starttls: bool,
    timeout: int = IMAP_TIMEOUT,
) -> imaplib.IMAP4:
    """Open IMAP. Port 993 is always implicit SSL (Gmail/Outlook IMAPS).

    ``use_starttls`` is the SMTP checkbox in the connect form. It must not
    force a plaintext IMAP greeting on 993 — Gmail waits for TLS there and
    the client times out, so sync looks successful later while the inbox
    stays empty.
    """
    port = int(port or 993)
    imaplib._MAXLINE = 50_000_000
    if port == 993 or (use_tls and port != 143):
        return imaplib.IMAP4_SSL(host, port, timeout=timeout)
    conn = imaplib.IMAP4(host, port, timeout=timeout)
    if use_starttls or port == 143:
        conn.starttls()
    return conn


def send_imap_id(conn: imaplib.IMAP4) -> None:
    """RFC 2971 IMAP ID. Best-effort; some hosts require it after LOGIN."""
    try:
        conn.xatom("ID", '("name" "keprix" "vendor" "Keprix")')
    except Exception:
        logger.debug("IMAP ID command not accepted", exc_info=True)


def imap_login(conn: imaplib.IMAP4, username: str, password: str | None = None, *, access_token: str | None = None) -> None:
    if access_token:

        def _auth(_challenge: bytes | None = None) -> bytes:
            return f"user={username}\x01auth=Bearer {access_token}\x01\x01".encode("utf-8")

        conn.authenticate("XOAUTH2", _auth)
        return
    if not password:
        raise ValueError("IMAP password or OAuth access token is required")
    conn.login(username, password)


@contextmanager
def imap_session(account: dict[str, Any]):
    conn = open_imap_connection(
        account["imap_host"],
        int(account.get("imap_port") or 993),
        use_tls=bool(account.get("use_tls", True)),
        use_starttls=bool(account.get("use_starttls", False)),
    )
    try:
        access_token = str(account.get("access_token") or "").strip() or None
        password = account.get("password")
        if not password and account.get("password_encrypted"):
            password = decrypt_secret(account["password_encrypted"])
        username = str(account.get("username") or account.get("email_address") or "").strip()
        imap_login(conn, username, password, access_token=access_token)
        send_imap_id(conn)
        yield conn
    finally:
        try:
            conn.logout()
        except Exception:
            pass


def list_imap_folders(conn: imaplib.IMAP4) -> list[str]:
    status, folders = conn.list()
    if status != "OK" or not folders:
        return []
    names: list[str] = []
    for entry in folders:
        decoded = entry.decode() if isinstance(entry, bytes) else str(entry)
        match = re.search(r'"([^"]*)"\s*$|(\S+)\s*$', decoded)
        if match:
            names.append(match.group(1) or match.group(2))
    return names


def test_imap_smtp(account: dict[str, Any]) -> dict[str, Any]:
    cfg = dict(account)
    if not cfg.get("access_token") and cfg.get("password_encrypted") and not cfg.get("password"):
        cfg["password"] = decrypt_secret(cfg.get("password_encrypted", ""))
    folders: list[str] = []
    with imap_session(cfg) as conn:
        folders = list_imap_folders(conn)

    # SMTP auth probe without sending mail.
    probe = MIMEText("keprix connection test", "plain", "utf-8")
    probe["Subject"] = "Keprix connection test"
    probe["From"] = cfg.get("email_address") or cfg["username"]
    probe["To"] = cfg.get("email_address") or cfg["username"]
    security = smtp_security_mode(int(cfg["smtp_port"]), bool(cfg.get("use_starttls")))
    host = cfg["smtp_host"]
    port = int(cfg["smtp_port"])
    username = cfg["username"]
    access_token = str(cfg.get("access_token") or "").strip() or None
    password = cfg.get("password")

    def _auth(smtp: smtplib.SMTP) -> None:
        if access_token:
            import base64

            auth_str = base64.b64encode(f"user={username}\x01auth=Bearer {access_token}\x01\x01".encode("utf-8")).decode(
                "ascii"
            )
            code, response = smtp.docmd("AUTH", f"XOAUTH2 {auth_str}")
            if code != 235:
                raise smtplib.SMTPAuthenticationError(code, response)
            return
        smtp.login(username, password or "")

    if security == "ssl":
        with smtplib.SMTP_SSL(host, port, timeout=IMAP_TIMEOUT) as smtp:
            _auth(smtp)
    else:
        with smtplib.SMTP(host, port, timeout=IMAP_TIMEOUT) as smtp:
            if security == "starttls":
                smtp.starttls()
            _auth(smtp)
    return {"ok": True, "folders": folders[:20], "smtp": "ok"}


def extract_text_body(msg: email_mod.message.Message) -> str:
    if msg.is_multipart():
        text_parts: list[str] = []
        for part in msg.walk():
            ct = part.get_content_type()
            cd = str(part.get("Content-Disposition", ""))
            if ct == "text/plain" and "attachment" not in cd:
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or "utf-8"
                    text_parts.append(payload.decode(charset, errors="replace"))
            elif ct == "text/html" and not text_parts and "attachment" not in cd:
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or "utf-8"
                    raw_html = payload.decode(charset, errors="replace")
                    text = re.sub(r"<br\s*/?>", "\n", raw_html, flags=re.I)
                    text = re.sub(r"<[^>]+>", "", text)
                    text_parts.append(html.unescape(text).strip())
        return "\n".join(text_parts)
    payload = msg.get_payload(decode=True)
    if payload:
        charset = msg.get_content_charset() or "utf-8"
        return payload.decode(charset, errors="replace")
    return ""


def extract_html_body(msg: email_mod.message.Message) -> str | None:
    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            cd = str(part.get("Content-Disposition", ""))
            if ct == "text/html" and "attachment" not in cd:
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or "utf-8"
                    return payload.decode(charset, errors="replace")
    elif msg.get_content_type() == "text/html":
        payload = msg.get_payload(decode=True)
        if payload:
            charset = msg.get_content_charset() or "utf-8"
            return payload.decode(charset, errors="replace")
    return None


def has_attachments(msg: email_mod.message.Message) -> bool:
    if not msg.is_multipart():
        return False
    for part in msg.walk():
        if part.is_multipart():
            continue
        cd = str(part.get("Content-Disposition", ""))
        if "attachment" in cd.lower():
            return True
    return False


def parse_addresses(raw: str | None) -> list[str]:
    if not raw:
        return []
    return [addr for _, addr in email.utils.getaddresses([raw]) if addr]


def _strip_msgid(value: str | None) -> str | None:
    raw = (value or "").strip()
    if not raw:
        return None
    if raw.startswith("<") and raw.endswith(">"):
        return raw[1:-1].strip() or None
    return raw


def _parse_references_header(raw: str | None) -> list[str]:
    if not raw:
        return []
    tokens: list[str] = []
    for match in re.finditer(r"<([^>]+)>|(\S+)", str(raw)):
        token = _strip_msgid(match.group(1) or match.group(2) or "")
        if token and token not in tokens:
            tokens.append(token)
    return tokens


def parse_message(
    raw_bytes: bytes,
    *,
    uid: int | None,
    folder: str,
) -> dict[str, Any]:
    msg = email_mod.message_from_bytes(raw_bytes)
    from_name, from_addr = email.utils.parseaddr(decode_header_value(msg.get("From")))
    subject = decode_header_value(msg.get("Subject"))
    message_id = (msg.get("Message-ID") or "").strip() or f"local-{uid or 0}@{folder}"
    body_text = extract_text_body(msg)
    preview = (body_text or "")[:200]
    date_hdr = msg.get("Date")
    received_at = datetime.now(timezone.utc)
    if date_hdr:
        try:
            received_at = email.utils.parsedate_to_datetime(date_hdr)
            if received_at.tzinfo is None:
                received_at = received_at.replace(tzinfo=timezone.utc)
        except Exception:
            pass
    attachments_meta: list[dict[str, Any]] = []
    try:
        from keprix.outreach.inbound_mail import extract_attachment_meta_from_email_message

        attachments_meta = extract_attachment_meta_from_email_message(msg)
    except Exception:
        attachments_meta = []
    return {
        "message_id": message_id,
        "uid": uid,
        "folder": folder,
        "from_address": from_addr or "unknown",
        "from_name": from_name or None,
        "to_addresses": parse_addresses(msg.get("To")),
        "cc_addresses": parse_addresses(msg.get("Cc")),
        "subject": subject or "",
        "body_text": body_text or None,
        "body_html": extract_html_body(msg),
        "preview": preview or None,
        "has_attachments": has_attachments(msg),
        "attachments_meta": attachments_meta,
        "in_reply_to": _strip_msgid(msg.get("In-Reply-To")),
        "references": _parse_references_header(msg.get("References")),
        "received_at": received_at,
    }


def _select_folder(conn: imaplib.IMAP4, folder: str) -> None:
    typ, data = conn.select(quote_mailbox(folder), readonly=True)
    if typ != "OK":
        typ, data = conn.select(folder, readonly=True)
    if typ != "OK":
        raise RuntimeError(f"IMAP could not open folder {folder}: {typ} {data}")


def _search_uids(conn: imaplib.IMAP4) -> list[bytes]:
    for criteria in ("ALL", "1:*"):
        status, data = conn.uid("SEARCH", None, criteria)
        if status == "OK" and data and data[0]:
            return data[0].split()
    return []


def _rfc822_payloads(fetched: Any) -> list[bytes]:
    payloads: list[bytes] = []
    for item in fetched or []:
        if isinstance(item, tuple) and len(item) >= 2 and isinstance(item[1], (bytes, bytearray)):
            payloads.append(bytes(item[1]))
    return payloads


def _fetch_folder(conn: imaplib.IMAP4, folder: str, *, limit: int = 50) -> list[dict[str, Any]]:
    _select_folder(conn, folder)
    results: list[dict[str, Any]] = []
    for uid_b in _search_uids(conn)[-limit:]:
        uid = int(uid_b)
        st, fetched = conn.uid("FETCH", uid_b, "(RFC822)")
        if st != "OK" or not fetched:
            st, fetched = conn.uid("FETCH", uid_b, "(BODY.PEEK[])")
        if st != "OK" or not fetched:
            continue
        for raw in _rfc822_payloads(fetched):
            results.append(parse_message(raw, uid=uid, folder=folder))
    return results


def _fallback_folders(conn: imaplib.IMAP4, requested: str) -> list[str]:
    names: list[str] = []
    try:
        names = list_imap_folders(conn)
    except Exception:
        logger.debug("IMAP LIST failed", exc_info=True)
    extras: list[str] = []
    for name in names:
        lowered = name.lower()
        if lowered.endswith("all mail") or lowered in {"all", "archive"}:
            extras.append(name)
    ordered = [requested]
    for name in extras:
        if name not in ordered:
            ordered.append(name)
    return ordered


def fetch_new_messages(account: dict[str, Any], folder: str = "INBOX") -> list[dict[str, Any]]:
    password = account.get("password")
    if not password:
        password = decrypt_secret(account.get("password_encrypted", ""))
    username = str(account.get("username") or account.get("email_address") or "").strip()
    cfg = {**account, "password": password, "username": username}
    with imap_session(cfg) as conn:
        for candidate in _fallback_folders(conn, folder or "INBOX"):
            try:
                results = _fetch_folder(conn, candidate)
            except Exception:
                logger.exception("IMAP fetch failed for folder %s", candidate)
                continue
            if results:
                return results
    return []


def send_smtp_message(
    account: dict[str, Any],
    *,
    from_addr: str,
    to_addresses: list[str],
    cc_addresses: list[str],
    subject: str,
    body: str,
) -> dict[str, Any]:
    access_token = str(account.get("access_token") or "").strip() or None
    password = account.get("password")
    if password is None and account.get("password_encrypted"):
        password = decrypt_secret(account.get("password_encrypted", ""))
    recipients = list(dict.fromkeys([*to_addresses, *cc_addresses]))
    message = MIMEMultipart()
    message["From"] = from_addr
    message["To"] = ", ".join(to_addresses)
    if cc_addresses:
        message["Cc"] = ", ".join(cc_addresses)
    message["Subject"] = subject
    from email.utils import make_msgid

    domain = from_addr.split("@")[-1] if "@" in from_addr else "keprix.local"
    message_id = make_msgid(domain=domain)
    message["Message-ID"] = message_id
    message.attach(MIMEText(body, "plain", "utf-8"))

    security = smtp_security_mode(int(account["smtp_port"]), bool(account.get("use_starttls")))
    host = account["smtp_host"]
    port = int(account["smtp_port"])
    raw = message.as_string()
    username = account["username"]

    def _smtp_auth(smtp: smtplib.SMTP) -> None:
        if access_token:
            import base64

            auth_str = base64.b64encode(f"user={username}\x01auth=Bearer {access_token}\x01\x01".encode("utf-8")).decode(
                "ascii"
            )
            code, response = smtp.docmd("AUTH", f"XOAUTH2 {auth_str}")
            if code != 235:
                raise smtplib.SMTPAuthenticationError(code, response)
            return
        if not password:
            raise ValueError("SMTP password or OAuth access token is required")
        smtp.login(username, password)

    if security == "ssl":
        with smtplib.SMTP_SSL(host, port, timeout=IMAP_TIMEOUT) as smtp:
            _smtp_auth(smtp)
            smtp.sendmail(from_addr, recipients, raw)
    else:
        with smtplib.SMTP(host, port, timeout=IMAP_TIMEOUT) as smtp:
            if security == "starttls":
                smtp.starttls()
            _smtp_auth(smtp)
            smtp.sendmail(from_addr, recipients, raw)
    return {"message_id": str(message_id).strip("<>"), "provider_message_id": str(message_id).strip("<>")}


async def resolve_account_connection(account: Any) -> dict[str, Any]:
    """Build IMAP/SMTP connection dict, resolving OAuth access tokens when needed."""
    if hasattr(account, "to_connection"):
        payload = account.to_connection()
        user_id = account.user_id
        oauth_provider = getattr(account, "oauth_provider", None)
        vault_id = getattr(account, "oauth_vault_item_id", None)
    else:
        payload = dict(account)
        user_id = str(payload.get("user_id") or "")
        oauth_provider = payload.get("oauth_provider")
        vault_id = payload.get("oauth_vault_item_id")

    if vault_id and oauth_provider == "google":
        from keprix.oauth.tokens import refresh_google_tokens

        tokens = await refresh_google_tokens(vault_id, user_id)
        payload["access_token"] = tokens.get("access_token")
    elif vault_id and oauth_provider == "microsoft":
        from keprix.oauth.tokens import load_oauth_tokens

        tokens = await load_oauth_tokens(vault_id, user_id)
        payload["access_token"] = tokens.get("access_token")
    elif payload.get("password_encrypted") and not payload.get("password"):
        try:
            payload["password"] = decrypt_secret(payload["password_encrypted"])
        except Exception:
            payload["password"] = ""
    return payload
