"""Persistent export file store."""

from __future__ import annotations

import json
import re
import secrets
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _exports_dir() -> Path:
    try:
        from keprix_cli.config import get_keprix_home

        root = Path(get_keprix_home()) / "exports"
    except Exception:
        root = Path.home() / ".keprix" / "exports"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _slugify(title: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", title.strip().lower()).strip("-")
    return slug[:48] or "export"


@dataclass
class ExportRecord:
    file_id: str
    filename: str
    mime: str
    format_returned: str
    size_bytes: int
    created_at: str
    title: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ExportStore:
    def __init__(self, base_dir: Path | None = None) -> None:
        self._dir = base_dir or _exports_dir()
        self._index_path = self._dir / "index.json"
        self._records: dict[str, ExportRecord] = {}
        self._load()

    def _load(self) -> None:
        if not self._index_path.exists():
            return
        rows = json.loads(self._index_path.read_text(encoding="utf-8"))
        for row in rows:
            record = ExportRecord(**row)
            self._records[record.file_id] = record

    def _save_index(self) -> None:
        rows = [record.to_dict() for record in self._records.values()]
        self._index_path.write_text(json.dumps(rows, indent=2), encoding="utf-8")

    def save(
        self,
        *,
        title: str,
        content: str | bytes,
        mime: str,
        format_returned: str,
    ) -> ExportRecord:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        ext = "pdf" if format_returned == "pdf" else "html" if format_returned == "html" else "md"
        filename = f"{timestamp}-{_slugify(title)}.{ext}"
        file_id = secrets.token_hex(8)
        path = self._dir / f"{file_id}-{filename}"
        if isinstance(content, bytes):
            path.write_bytes(content)
            size = len(content)
        else:
            path.write_text(content, encoding="utf-8")
            size = len(content.encode("utf-8"))
        record = ExportRecord(
            file_id=file_id,
            filename=filename,
            mime=mime,
            format_returned=format_returned,
            size_bytes=size,
            created_at=datetime.now(timezone.utc).isoformat(),
            title=title,
        )
        self._records[file_id] = record
        self._save_index()
        record_path = self._dir / f"{file_id}.path"
        record_path.write_text(path.name, encoding="utf-8")
        return record

    def get(self, file_id: str) -> ExportRecord | None:
        return self._records.get(file_id)

    def resolve_path(self, file_id: str) -> Path | None:
        record = self.get(file_id)
        if record is None:
            return None
        marker = self._dir / f"{file_id}.path"
        if marker.exists():
            return self._dir / marker.read_text(encoding="utf-8").strip()
        candidates = list(self._dir.glob(f"{file_id}-*"))
        return candidates[0] if candidates else None


_store: ExportStore | None = None


def get_export_store() -> ExportStore:
    global _store
    if _store is None:
        _store = ExportStore()
    return _store
