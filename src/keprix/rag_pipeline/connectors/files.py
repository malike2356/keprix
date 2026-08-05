"""Filesystem / vault / URL source connectors for RAG ingest."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from urllib.request import Request, urlopen


class LocalFileSourceConnector:
    """Load local files or vault-relative markdown/text paths."""

    def __init__(self, path: str, *, vault_root: str | None = None) -> None:
        self.path = path.strip()
        self.vault_root = Path(vault_root).expanduser() if vault_root else None

    def resolve_path(self) -> Path:
        candidate = Path(self.path).expanduser()
        if not candidate.is_absolute() and self.vault_root is not None:
            candidate = (self.vault_root / self.path).resolve()
        else:
            candidate = candidate.resolve()
        if not candidate.is_file():
            raise FileNotFoundError(f"File not found: {candidate}")
        return candidate

    def fetch_document(self) -> dict[str, Any]:
        target = self.resolve_path()
        text = target.read_text(encoding="utf-8", errors="replace")
        source_type = "markdown" if target.suffix.lower() in {".md", ".markdown"} else "plaintext"
        return {
            "id": str(target),
            "content": text,
            "source_type": source_type,
            "path": str(target),
        }


class UrlSourceConnector:
    """Fetch a remote URL as plaintext/markdown when allowed."""

    def __init__(self, url: str, *, timeout_sec: float = 20.0) -> None:
        self.url = url.strip()
        self.timeout_sec = timeout_sec

    def fetch_document(self) -> dict[str, Any]:
        parsed = urlparse(self.url)
        if parsed.scheme not in {"http", "https"}:
            raise ValueError("Only http(s) URLs are supported")
        request = Request(self.url, headers={"User-Agent": "keprix-rag-pipeline/1.0"})
        with urlopen(request, timeout=self.timeout_sec) as response:  # noqa: S310
            raw = response.read()
            charset = "utf-8"
            content_type = response.headers.get_content_charset()
            if content_type:
                charset = content_type
            text = raw.decode(charset, errors="replace")
        source_type = "markdown" if self.url.lower().endswith((".md", ".markdown")) else "plaintext"
        return {
            "id": self.url,
            "content": text,
            "source_type": source_type,
            "url": self.url,
        }
