"""Gateway adapters for Document Vault channel ops (Prompt 651)."""

from __future__ import annotations

import base64
from typing import Any

from keprix.document_vault.channel.commands import looks_like_vault_import_caption
from keprix.document_vault.channel.contract import ChannelAttachment
from keprix.document_vault.channel.import_pipeline import import_channel_attachment
from keprix.document_vault.flags import load_flags
from keprix.document_vault.models import VaultError


def try_import_channel_file(
    *,
    platform: str,
    channel_user_id: str,
    event_id: str,
    filename: str,
    data: bytes,
    declared_mime: str = "",
    caption: str = "",
    parent_id: str | None = None,
) -> dict[str, Any] | None:
    """Import when vault channel ops enabled and caption asks to save.

    Returns None when the caption is not a vault import intent (caller keeps
    normal media handling). Raises VaultError for policy failures.
    """
    flags = load_flags()
    if not flags.enabled or not flags.channel_ops:
        return None
    if not looks_like_vault_import_caption(caption) and not caption.strip().lower().startswith("/vault import"):
        return None
    receipt = import_channel_attachment(
        ChannelAttachment(
            platform=platform,
            channel_user_id=channel_user_id,
            event_id=event_id,
            filename=filename or "upload.bin",
            data=data,
            declared_mime=declared_mime,
            caption=caption,
            parent_id=parent_id,
        )
    )
    return {
        "ok": receipt.ok,
        "message": receipt.message,
        "item_id": receipt.item_id,
        "job_id": receipt.job_id,
        "deduplicated": receipt.deduplicated,
        "data": receipt.data,
    }


def attachment_meta_from_bytes(
    *,
    event_id: str,
    filename: str,
    data: bytes,
    mime: str = "",
) -> dict[str, Any]:
    """Build slash metadata for /vault import when the file is already in memory."""
    return {
        "event_id": event_id,
        "attachment_filename": filename,
        "attachment_base64": base64.b64encode(data).decode("ascii"),
        "mime": mime,
    }


def safe_try_import(**kwargs: Any) -> dict[str, Any] | None:
    try:
        return try_import_channel_file(**kwargs)
    except VaultError as exc:
        return {"ok": False, "error_code": exc.code, "error": exc.message, **(exc.extra or {})}


__all__ = [
    "attachment_meta_from_bytes",
    "safe_try_import",
    "try_import_channel_file",
]
