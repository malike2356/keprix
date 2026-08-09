"""Document Vault domain constants and helpers (Prompt 646)."""

from __future__ import annotations

import hashlib
import re
from typing import Any

ITEM_KINDS: tuple[str, ...] = (
    "folder",
    "rich_document",
    "spreadsheet",
    "presentation",
    "markdown",
    "html",
    "plain_text",
    "pdf",
    "binary_upload",
)

CONTENT_AUTHORITIES: tuple[str, ...] = ("workspace", "google")

KIND_MIME: dict[str, str] = {
    "folder": "application/vnd.keprix.folder",
    "rich_document": "application/vnd.keprix.rich-document",
    "spreadsheet": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "presentation": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "markdown": "text/markdown",
    "html": "text/html",
    "plain_text": "text/plain",
    "pdf": "application/pdf",
    "binary_upload": "application/octet-stream",
}

KIND_EXTENSION: dict[str, str] = {
    "folder": "",
    "rich_document": ".keprixdoc",
    "spreadsheet": ".xlsx",
    "presentation": ".pptx",
    "markdown": ".md",
    "html": ".html",
    "plain_text": ".txt",
    "pdf": ".pdf",
    "binary_upload": "",
}

INDEX_POLICIES: tuple[str, ...] = ("inherit", "index", "skip")


class VaultError(Exception):
    def __init__(self, code: str, message: str = "", **extra: Any) -> None:
        super().__init__(message or code)
        self.code = code
        self.message = message or code
        self.extra = extra

    def as_dict(self) -> dict[str, Any]:
        return {"ok": False, "error_code": self.code, "message": self.message, **self.extra}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


_UNSAFE_NAME = re.compile(r"[\x00-\x1f\x7f<>:\"|?*\\/]+")


def sanitize_name(name: str, *, max_len: int = 255) -> str:
    cleaned = _UNSAFE_NAME.sub("_", (name or "").strip()) or "Untitled"
    cleaned = cleaned.replace("..", "_")
    if cleaned in {".", ".."} or not cleaned.strip("._"):
        cleaned = "Untitled"
    return cleaned[:max_len]


def normalize_mime(kind: str, mime: str | None = None) -> str:
    if mime and mime.strip():
        return mime.strip().lower()
    return KIND_MIME.get(kind, "application/octet-stream")


def extension_for(kind: str, name: str = "") -> str:
    if kind == "binary_upload" and "." in name:
        return "." + name.rsplit(".", 1)[-1].lower()[:32]
    return KIND_EXTENSION.get(kind, "")


def format_to_kind(fmt: str | None) -> str:
    f = (fmt or "markdown").strip().lower()
    mapping = {
        "markdown": "markdown",
        "md": "markdown",
        "html": "html",
        "text": "plain_text",
        "plain": "plain_text",
        "txt": "plain_text",
        "pdf": "pdf",
        "rich": "rich_document",
    }
    return mapping.get(f, "markdown")
