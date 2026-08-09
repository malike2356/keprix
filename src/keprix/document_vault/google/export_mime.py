"""Documented Google Drive export / native MIME mappings (Prompt 649)."""

from __future__ import annotations

# Google Workspace native MIME types.
GOOGLE_DOC = "application/vnd.google-apps.document"
GOOGLE_SHEET = "application/vnd.google-apps.spreadsheet"
GOOGLE_SLIDE = "application/vnd.google-apps.presentation"
GOOGLE_FOLDER = "application/vnd.google-apps.folder"

# Export MIME targets (Google Docs export API).
EXPORT_MIME: dict[str, dict[str, str]] = {
    GOOGLE_DOC: {
        "markdown": "text/markdown",
        "html": "text/html",
        "pdf": "application/pdf",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "txt": "text/plain",
    },
    GOOGLE_SHEET: {
        "csv": "text/csv",
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "pdf": "application/pdf",
    },
    GOOGLE_SLIDE: {
        "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "pdf": "application/pdf",
    },
}

# Vault kind -> Google create MIME (native Docs/Sheets/Slides when preferred).
VAULT_KIND_TO_GOOGLE_CREATE: dict[str, str] = {
    "folder": GOOGLE_FOLDER,
    "rich_document": GOOGLE_DOC,
    "markdown": GOOGLE_DOC,
    "html": GOOGLE_DOC,
    "plain_text": "text/plain",
    "spreadsheet": GOOGLE_SHEET,
    "presentation": GOOGLE_SLIDE,
    "pdf": "application/pdf",
    "binary_upload": "application/octet-stream",
}

GOOGLE_MIME_TO_VAULT_KIND: dict[str, str] = {
    GOOGLE_FOLDER: "folder",
    GOOGLE_DOC: "rich_document",
    GOOGLE_SHEET: "spreadsheet",
    GOOGLE_SLIDE: "presentation",
    "application/pdf": "pdf",
    "text/markdown": "markdown",
    "text/html": "html",
    "text/plain": "plain_text",
}


def export_mime_for(google_mime: str, format_name: str) -> str | None:
    table = EXPORT_MIME.get(google_mime) or {}
    return table.get(format_name.lower())


def vault_kind_for_google_mime(mime: str) -> str:
    if mime in GOOGLE_MIME_TO_VAULT_KIND:
        return GOOGLE_MIME_TO_VAULT_KIND[mime]
    if mime.startswith("text/"):
        return "plain_text"
    return "binary_upload"


def google_create_mime_for_kind(kind: str) -> str:
    return VAULT_KIND_TO_GOOGLE_CREATE.get(kind, "application/octet-stream")


__all__ = [
    "EXPORT_MIME",
    "GOOGLE_DOC",
    "GOOGLE_FOLDER",
    "GOOGLE_SHEET",
    "GOOGLE_SLIDE",
    "GOOGLE_MIME_TO_VAULT_KIND",
    "VAULT_KIND_TO_GOOGLE_CREATE",
    "export_mime_for",
    "google_create_mime_for_kind",
    "vault_kind_for_google_mime",
]
