"""Optional IMAP email ingest for spreadsheet attachments (disabled by default).

Set ``KEPRIX_SHEET_EMAIL_INGEST=1`` to enable polling. Soft Wall still gates any
CRM write; this module downloads CSV/XLSX attachments into the sheet upload dir
and either proposes sheet Soft Wall jobs or calls ``ingest_channel_attachment``.

Default: disabled (``KEPRIX_SHEET_EMAIL_INGEST=0``).

Do **not** use this path for campaign reply reconciliation (Prompt 626 owns replies).
"""

from __future__ import annotations

import email as email_mod
import os
from pathlib import Path
from typing import Any, Callable


SHEET_SUFFIXES = {".csv", ".tsv", ".xlsx"}


def email_ingest_enabled() -> bool:
    raw = os.environ.get("KEPRIX_SHEET_EMAIL_INGEST", "0").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def status() -> dict[str, Any]:
    return {
        "enabled": email_ingest_enabled(),
        "env": "KEPRIX_SHEET_EMAIL_INGEST",
        "default": "0",
        "note": (
            "When enabled, authorised spreadsheet attachments download via IMAP, "
            "save via sheet_preprocess.save_upload, then propose Soft Wall enrich "
            "or ingest_channel_attachment. CRM writes still require Soft Wall apply. "
            "Not used for campaign reply reconciliation."
        ),
    }


def _extract_sheet_attachments(msg: email_mod.message.Message) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if not msg.is_multipart():
        return out
    for part in msg.walk():
        if part.is_multipart():
            continue
        disposition = str(part.get("Content-Disposition", "") or "")
        filename = part.get_filename()
        if not filename and "attachment" not in disposition.lower():
            continue
        name = Path(str(filename or "attachment.bin")).name
        suffix = Path(name).suffix.lower()
        if suffix not in SHEET_SUFFIXES:
            continue
        payload = part.get_payload(decode=True)
        if not isinstance(payload, (bytes, bytearray)) or not payload:
            continue
        out.append({"filename": name, "content": bytes(payload), "content_type": part.get_content_type()})
    return out


def _resolve_imap_accounts(workspace_id: str) -> list[dict[str, Any]]:
    """Best-effort account list for tests/operators; vault credentials optional."""
    accounts: list[dict[str, Any]] = []
    # Allow inject via env JSON path for operators (no secrets invented).
    raw_path = os.environ.get("KEPRIX_SHEET_EMAIL_INGEST_ACCOUNTS_FILE", "").strip()
    if raw_path and Path(raw_path).is_file():
        import json

        try:
            data = json.loads(Path(raw_path).read_text(encoding="utf-8"))
            if isinstance(data, list):
                accounts.extend([a for a in data if isinstance(a, dict)])
        except Exception:
            pass
    return accounts


def poll_once(
    *,
    workspace_id: str = "default",
    fetch_messages: Callable[[dict[str, Any]], list[dict[str, Any]]] | None = None,
    accounts: list[dict[str, Any]] | None = None,
    mode: str = "propose",
) -> dict[str, Any]:
    """
    Poll IMAP (or injected fetcher) for spreadsheet attachments.

    ``mode``:
      - ``propose`` (default): save_upload + propose_sheet (Soft Wall before CRM write)
      - ``ingest``: ingest_channel_attachment (still auditable; Soft Wall for enrich apply)

    When disabled, returns structured skip. Tests inject ``fetch_messages``.
    """
    if not email_ingest_enabled():
        return {
            "ok": True,
            "skipped": True,
            "reason": "email_ingest_disabled",
            "status": status(),
            "workspace_id": workspace_id,
            "ingested": [],
        }

    account_list = list(accounts or _resolve_imap_accounts(workspace_id))
    if fetch_messages is None and not account_list:
        return {
            "ok": True,
            "skipped": True,
            "reason": "email_ingest_not_configured",
            "status": status(),
            "workspace_id": workspace_id,
            "ingested": [],
            "hint": (
                "Bind IMAP accounts (KEPRIX_SHEET_EMAIL_INGEST_ACCOUNTS_FILE) "
                "or inject fetch_messages for tests. Soft Wall still required before CRM apply."
            ),
        }

    from keprix.crm.soft_wall import gate_or_approve
    from keprix.sheet_preprocess import service as sheet_service

    ingested: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    def _default_fetch(account: dict[str, Any]) -> list[dict[str, Any]]:
        from keprix.email.helpers import fetch_new_messages

        return fetch_new_messages(account)

    fetcher = fetch_messages or _default_fetch
    # When only fetch_messages is provided (tests), use a synthetic account slot.
    iterate = account_list or [{"id": "injected", "username": "test"}]

    for account in iterate:
        try:
            messages = fetcher(account)
        except Exception as exc:
            errors.append({"account": account.get("id") or account.get("username"), "error": str(exc)})
            continue
        for message in messages or []:
            raw = message.get("raw_bytes") or message.get("rfc822")
            attachments: list[dict[str, Any]] = []
            if isinstance(raw, (bytes, bytearray)):
                msg = email_mod.message_from_bytes(bytes(raw))
                attachments = _extract_sheet_attachments(msg)
            elif message.get("attachments"):
                for att in message["attachments"]:
                    name = Path(str(att.get("filename") or "upload.csv")).name
                    if Path(name).suffix.lower() not in SHEET_SUFFIXES:
                        continue
                    content = att.get("content") or att.get("bytes")
                    if isinstance(content, (bytes, bytearray)) and content:
                        attachments.append({"filename": name, "content": bytes(content)})

            for att in attachments:
                try:
                    meta = sheet_service.save_upload(
                        workspace_id,
                        filename=att["filename"],
                        content=att["content"],
                        actor_type="email_ingest",
                        actor_id=str(account.get("id") or account.get("username") or "imap"),
                    )
                    item: dict[str, Any] = {
                        "upload": meta,
                        "filename": att["filename"],
                        "from_address": message.get("from_address"),
                        "subject": message.get("subject"),
                    }
                    if mode == "ingest":
                        from keprix.crm.ingestion import ingest_channel_attachment

                        # Soft Wall before treating as authorised CRM write path
                        gate = gate_or_approve(
                            workspace_id,
                            kind="crm_integration_import",
                            subject=f"Email sheet ingest {att['filename']}",
                            payload={"upload_id": meta["upload_id"], "filename": att["filename"]},
                            object_type="enrichment_job",
                            object_id=meta["upload_id"],
                        )
                        item["soft_wall"] = gate
                        if gate.get("blocked"):
                            item["status"] = "soft_wall_required"
                        else:
                            result = ingest_channel_attachment(
                                workspace_id,
                                att["content"],
                                filename=att["filename"],
                                channel="email_ingest",
                            )
                            item["ingest"] = result
                            item["status"] = "ingested"
                    else:
                        job = sheet_service.propose_sheet(
                            workspace_id,
                            upload_id=meta["upload_id"],
                            actor_type="email_ingest",
                            actor_id=str(account.get("id") or "imap"),
                        )
                        gate = gate_or_approve(
                            workspace_id,
                            kind="apply_enrichment",
                            subject=f"Email sheet propose {att['filename']}",
                            payload={"upload_id": meta["upload_id"], "job_id": job.get("id")},
                            object_type="enrichment_job",
                            object_id=str(job.get("id") or meta["upload_id"]),
                        )
                        item["job"] = job
                        item["soft_wall"] = gate
                        item["status"] = "proposed" if gate.get("blocked") else "ready_apply"
                    ingested.append(item)
                except Exception as exc:
                    errors.append({"filename": att.get("filename"), "error": str(exc)})

    return {
        "ok": True,
        "skipped": False,
        "status": status(),
        "workspace_id": workspace_id,
        "mode": mode,
        "ingested": ingested,
        "errors": errors,
        "count": len(ingested),
    }
