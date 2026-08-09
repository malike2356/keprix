"""Import safety: sniff, limits, macros, sanitization (Prompt 647)."""

from __future__ import annotations

import os
import zipfile
from io import BytesIO
from typing import Any

from keprix.document_vault.models import VaultError

# Defaults; override via env for operators.
DEFAULT_MAX_BYTES = int(os.environ.get("KEPRIX_DOCUMENT_VAULT_MAX_UPLOAD_BYTES") or 25 * 1024 * 1024)
DEFAULT_MAX_ARCHIVE_ENTRIES = int(os.environ.get("KEPRIX_DOCUMENT_VAULT_MAX_ARCHIVE_ENTRIES") or 2000)
DEFAULT_MAX_ARCHIVE_UNCOMPRESSED = int(
    os.environ.get("KEPRIX_DOCUMENT_VAULT_MAX_ARCHIVE_UNCOMPRESSED") or 100 * 1024 * 1024
)


SNIFF_MAGIC: tuple[tuple[bytes, str, str], ...] = (
    (b"%PDF", "application/pdf", ".pdf"),
    (b"PK\x03\x04", "application/zip", ".zip"),  # docx/xlsx/pptx/odt
    (b"\x89PNG\r\n\x1a\n", "image/png", ".png"),
    (b"\xff\xd8\xff", "image/jpeg", ".jpg"),
    (b"GIF87a", "image/gif", ".gif"),
    (b"GIF89a", "image/gif", ".gif"),
    (b"RIFF", "image/webp", ".webp"),
)


def sniff_mime(data: bytes, *, filename: str = "", declared_mime: str = "") -> dict[str, Any]:
    head = data[:64] if data else b""
    detected_mime = ""
    detected_ext = ""
    for magic, mime, ext in SNIFF_MAGIC:
        if head.startswith(magic):
            detected_mime = mime
            detected_ext = ext
            break
    if not detected_mime and data:
        try:
            text = data[:4096].decode("utf-8")
        except UnicodeDecodeError:
            detected_mime = "application/octet-stream"
        else:
            stripped = text.lstrip().lower()
            if stripped.startswith("<!doctype html") or stripped.startswith("<html"):
                detected_mime = "text/html"
                detected_ext = ".html"
            elif stripped.startswith("{") or stripped.startswith("["):
                detected_mime = "application/json"
                detected_ext = ".json"
            else:
                detected_mime = "text/plain"
                detected_ext = ".txt"
                name = filename.lower()
                if name.endswith(".md") or name.endswith(".markdown"):
                    detected_mime = "text/markdown"
                    detected_ext = ".md"
                elif name.endswith(".csv"):
                    detected_mime = "text/csv"
                    detected_ext = ".csv"

    declared = (declared_mime or "").split(";")[0].strip().lower()
    spoofed = bool(declared and detected_mime and declared != detected_mime and not _compatible(declared, detected_mime, filename))
    return {
        "declared_mime": declared,
        "detected_mime": detected_mime,
        "detected_ext": detected_ext,
        "spoofed": spoofed,
        "filename": filename,
    }


def _compatible(declared: str, detected: str, filename: str) -> bool:
    name = filename.lower()
    if detected == "application/zip":
        if declared.endswith("wordprocessingml.document") or name.endswith(".docx"):
            return True
        if declared.endswith("spreadsheetml.sheet") or name.endswith(".xlsx"):
            return True
        if declared.endswith("presentationml.presentation") or name.endswith(".pptx"):
            return True
        if "opendocument" in declared or name.endswith((".odt", ".ods")):
            return True
    if declared in {"text/markdown", "text/x-markdown"} and detected in {"text/plain", "text/markdown"}:
        return True
    if declared.startswith("text/") and detected.startswith("text/"):
        return True
    return declared == detected


def enforce_size_limits(data: bytes, *, max_bytes: int | None = None) -> None:
    if max_bytes is None:
        limit = int(os.environ.get("KEPRIX_DOCUMENT_VAULT_MAX_UPLOAD_BYTES") or DEFAULT_MAX_BYTES)
    else:
        limit = max_bytes
    if len(data) > limit:
        raise VaultError("quota_exceeded", f"file exceeds {limit} bytes", size=len(data), limit=limit)


def reject_office_macros(data: bytes, *, filename: str = "") -> list[str]:
    """Reject OOXML packages that contain macro parts."""
    warnings: list[str] = []
    name = filename.lower()
    if not (name.endswith((".docx", ".xlsx", ".pptx")) or data[:2] == b"PK"):
        return warnings
    try:
        with zipfile.ZipFile(BytesIO(data)) as zf:
            if len(zf.namelist()) > DEFAULT_MAX_ARCHIVE_ENTRIES:
                raise VaultError("quota_exceeded", "archive entry count too high")
            total = 0
            for info in zf.infolist():
                total += int(info.file_size or 0)
                if total > DEFAULT_MAX_ARCHIVE_UNCOMPRESSED:
                    raise VaultError("quota_exceeded", "archive uncompressed size too high")
                lower = info.filename.lower()
                if "vbaProject" in info.filename or lower.endswith(".bin") and "macro" in lower:
                    raise VaultError("unsupported_kind", "office macros are rejected")
                if lower.endswith((".exe", ".dll", ".js", ".vbs", ".bat", ".cmd", ".ps1")):
                    raise VaultError("unsupported_kind", "executable archive member rejected")
    except zipfile.BadZipFile:
        if name.endswith((".docx", ".xlsx", ".pptx", ".odt", ".ods")):
            raise VaultError("unsupported_kind", "corrupt office archive") from None
    return warnings


def sanitize_html(html: str) -> str:
    import nh3

    return nh3.clean(
        html or "",
        tags=nh3.ALLOWED_TAGS
        | {
            "h1",
            "h2",
            "h3",
            "h4",
            "h5",
            "h6",
            "pre",
            "code",
            "table",
            "thead",
            "tbody",
            "tr",
            "th",
            "td",
            "blockquote",
            "hr",
            "img",
            "div",
            "span",
        },
        attributes={"*": {"class", "id"}, "a": {"href", "title"}, "img": {"src", "alt", "title"}},
        link_rel=None,
    )


def malware_hook(data: bytes, *, filename: str = "") -> dict[str, Any]:
    """Placeholder hook for operator AV scanners (fail-open with audit note)."""
    # Intentionally no external network. Operators can replace via env later.
    _ = (data, filename)
    return {"scanned": False, "engine": "noop", "clean": True, "note": "noop scanner"}


def validate_upload(
    data: bytes,
    *,
    filename: str = "",
    declared_mime: str = "",
    max_bytes: int | None = None,
) -> dict[str, Any]:
    enforce_size_limits(data, max_bytes=max_bytes)
    sniff = sniff_mime(data, filename=filename, declared_mime=declared_mime)
    if sniff["spoofed"]:
        raise VaultError(
            "unsupported_kind",
            "MIME spoof detected",
            declared=sniff["declared_mime"],
            detected=sniff["detected_mime"],
        )
    warnings = reject_office_macros(data, filename=filename)
    scan = malware_hook(data, filename=filename)
    return {"sniff": sniff, "warnings": warnings, "malware": scan}
