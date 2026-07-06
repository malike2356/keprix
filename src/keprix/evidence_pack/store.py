"""Evidence pack metadata persistence."""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _pack_dir() -> Path:
    try:
        from keprix_cli.config import get_keprix_home

        root = Path(get_keprix_home()) / "evidence_packs"
    except Exception:
        root = Path.home() / ".keprix" / "evidence_packs"
    root.mkdir(parents=True, exist_ok=True)
    return root


@dataclass
class EvidencePackRecord:
    pack_id: str
    workspace_id: str
    status: str
    date_from: str
    date_to: str
    event_count: int
    document_count: int
    included_event_types: list[str]
    generated_at: str
    zip_path: str | None = None
    provider_submission_id: str | None = None
    provider_pack_url: str | None = None
    manifest_signature: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class EvidencePackStore:
    def __init__(self, base_dir: Path | None = None) -> None:
        self._dir = base_dir or _pack_dir()
        self._index_path = self._dir / "index.json"
        self._records: dict[str, EvidencePackRecord] = {}
        self._load()

    def _load(self) -> None:
        if not self._index_path.exists():
            return
        for row in json.loads(self._index_path.read_text(encoding="utf-8")):
            record = EvidencePackRecord(**row)
            self._records[record.pack_id] = record

    def _save(self) -> None:
        self._dir.mkdir(parents=True, exist_ok=True)
        rows = [record.to_dict() for record in self._records.values()]
        self._index_path.write_text(json.dumps(rows, indent=2), encoding="utf-8")

    def create_pending(
        self,
        *,
        workspace_id: str,
        date_from: str,
        date_to: str,
        included_event_types: list[str],
    ) -> EvidencePackRecord:
        pack_id = str(uuid.uuid4())
        record = EvidencePackRecord(
            pack_id=pack_id,
            workspace_id=workspace_id,
            status="generating",
            date_from=date_from,
            date_to=date_to,
            event_count=0,
            document_count=0,
            included_event_types=included_event_types,
            generated_at=datetime.now(timezone.utc).isoformat(),
        )
        self._records[pack_id] = record
        self._save()
        return record

    def mark_ready(
        self,
        pack_id: str,
        *,
        event_count: int,
        document_count: int,
        zip_path: str,
        manifest_signature: str,
    ) -> EvidencePackRecord | None:
        record = self._records.get(pack_id)
        if record is None:
            return None
        record.status = "ready"
        record.event_count = event_count
        record.document_count = document_count
        record.zip_path = zip_path
        record.manifest_signature = manifest_signature
        record.generated_at = datetime.now(timezone.utc).isoformat()
        self._save()
        return record

    def mark_failed(self, pack_id: str) -> None:
        record = self._records.get(pack_id)
        if record is None:
            return
        record.status = "failed"
        self._save()

    def set_provider_submission(self, pack_id: str, submission_id: str, provider_endpoint: str) -> None:
        record = self._records.get(pack_id)
        if record is None:
            return
        record.provider_submission_id = submission_id
        record.provider_pack_url = provider_endpoint
        self._save()

    def get(self, pack_id: str) -> EvidencePackRecord | None:
        return self._records.get(pack_id)

    def list_for_workspace(self, workspace_id: str) -> list[EvidencePackRecord]:
        return [row for row in self._records.values() if row.workspace_id == workspace_id]

    def zip_path(self, pack_id: str) -> Path | None:
        record = self.get(pack_id)
        if record is None or not record.zip_path:
            return None
        path = Path(record.zip_path)
        return path if path.exists() else None


_store: EvidencePackStore | None = None


def get_evidence_pack_store() -> EvidencePackStore:
    global _store
    if _store is None:
        _store = EvidencePackStore()
    return _store


def reset_evidence_pack_store() -> None:
    global _store
    _store = None
