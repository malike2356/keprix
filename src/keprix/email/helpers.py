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
    port = int(port or 993)
    if use_starttls:
        conn = imaplib.IMAP4(host, port, timeout=timeout)
        conn.starttls()
    elif use_tls or port == 993:
        conn = imaplib.IMAP4_SSL(host, port, timeout=timeout)
    else:
        conn = imaplib.IMAP4(host, port, timeout=timeout)
    imaplib._MAXLINE = 50_000_000
    return conn


def imap_login(conn: imaplib.IMAP4, username: str, password: str) -> None:
    conn.login(username, password)


@contextmanager
def imap_session(account: dict[str, Any]):
    conn = open_imap_connection(
        account["imap_host"],
        int(account["imap_port"]),
        use_tls=bool(account.get("use_tls", True)),
        use_starttls=bool(account.get("use_starttls", False)),
    )
    try:
        imap_login(conn, account["username"], account["password"])
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
    password = decrypt_secret(account.get("password_encrypted", ""))
    cfg = {**account, "password": password, "username": account["username"]}
    folders: list[str] = []
    with imap_session(cfg) as conn:
        folders = list_imap_folders(conn)

    security = smtp_security_mode(int(account["smtp_port"]), bool(account.get("use_starttls")))
    host = account["smtp_host"]
    port = int(account["smtp_port"])
    if security == "ssl":
        with smtplib.SMTP_SSL(host, port, timeout=IMAP_TIMEOUT) as smtp:
            smtp.login(account["username"], password)
    else:
        with smtplib.SMTP(host, port, timeout=IMAP_TIMEOUT) as smtp:
            if security == "starttls":
                smtp.starttls()
            smtp.login(account["username"], password)
    return {"ok": True, "folders": folders}


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
        "received_at": received_at,
    }


def fetch_new_messages(account: dict[str, Any], folder: str = "INBOX") -> list[dict[str, Any]]:
    password = decrypt_secret(account.get("password_encrypted", ""))
    cfg = {**account, "password": password, "username": account["username"]}
    results: list[dict[str, Any]] = []
    with imap_session(cfg) as conn:
        conn.select(quote_mailbox(folder), readonly=True)
        status, data = conn.uid("SEARCH", None, "ALL")
        if status != "OK" or not data or not data[0]:
            return results
        uids = data[0].split()
        for uid_b in uids[-50:]:
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


def send_smtp_message(
    account: dict[str, Any],
    *,
    from_addr: str,
    to_addresses: list[str],
    cc_addresses: list[str],
    subject: str,
    body: str,
) -> None:
    password = decrypt_secret(account.get("password_encrypted", ""))
    recipients = list(dict.fromkeys([*to_addresses, *cc_addresses]))
    message = MIMEMultipart()
    message["From"] = from_addr
    message["To"] = ", ".join(to_addresses)
    if cc_addresses:
        message["Cc"] = ", ".join(cc_addresses)
    message["Subject"] = subject
    message.attach(MIMEText(body, "plain", "utf-8"))

    security = smtp_security_mode(int(account["smtp_port"]), bool(account.get("use_starttls")))
    host = account["smtp_host"]
    port = int(account["smtp_port"])
    raw = message.as_string()
    if security == "ssl":
        with smtplib.SMTP_SSL(host, port, timeout=IMAP_TIMEOUT) as smtp:
            smtp.login(account["username"], password)
            smtp.sendmail(from_addr, recipients, raw)
        return
    with smtplib.SMTP(host, port, timeout=IMAP_TIMEOUT) as smtp:
        if security == "starttls":
            smtp.starttls()
        smtp.login(account["username"], password)
        smtp.sendmail(from_addr, recipients, raw)
