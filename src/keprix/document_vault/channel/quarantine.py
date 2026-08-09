"""Quarantine and scan inbound channel attachments before vault import."""

from __future__ import annotations

from typing import Any

from keprix.document_vault.formats.safety import malware_hook, validate_upload
from keprix.document_vault.models import VaultError


def quarantine_attachment(
    data: bytes,
    *,
    filename: str = "",
    declared_mime: str = "",
    max_bytes: int | None = None,
) -> dict[str, Any]:
    """Sniff MIME, enforce size, reject macros/spoofing, run AV hook."""
    if not data:
        raise VaultError("invalid_args", "empty attachment")
    validation = validate_upload(
        data,
        filename=filename,
        declared_mime=declared_mime,
        max_bytes=max_bytes,
    )
    scan = malware_hook(data, filename=filename)
    if scan.get("clean") is False:
        raise VaultError("malware_detected", "attachment failed malware scan", scan=scan)
    return {
        "ok": True,
        "validation": validation,
        "scan": scan,
        "quarantined": True,
    }


__all__ = ["quarantine_attachment"]
