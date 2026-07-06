"""Domain pack persistence (Prompt 30)."""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from keprix.backend.domain_packs.schemas import DomainPackManifest


def _packs_dir() -> Path:
    env = os.environ.get("KEPRIX_DATA_DIR", "").strip()
    if env:
        root = Path(env) / "domain_packs"
    else:
        try:
            from keprix_cli.config import get_keprix_home

            root = Path(get_keprix_home()) / "domain_packs"
        except Exception:
            root = Path.home() / ".keprix" / "domain_packs"
    root.mkdir(parents=True, exist_ok=True)
    return root


class DomainPackStore:
    def __init__(self, base_dir: Path | None = None) -> None:
        self._dir = base_dir or _packs_dir()
        self._dir.mkdir(parents=True, exist_ok=True)
        self._index_path = self._dir / "index.json"

    def _read_index(self) -> dict[str, str]:
        if not self._index_path.exists():
            return {}
        return json.loads(self._index_path.read_text(encoding="utf-8"))

    def _write_index(self, data: dict[str, str]) -> None:
        self._index_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def _pack_path(self, pack_id: str) -> Path:
        return self._dir / f"{pack_id}.json"

    def list_packs(self) -> list[DomainPackManifest]:
        rows: list[DomainPackManifest] = []
        for pack_id in self._read_index().values():
            pack = self.get_pack(pack_id)
            if pack is not None:
                rows.append(pack)
        return sorted(rows, key=lambda row: row.domain_name)

    def get_pack(self, pack_id: str) -> DomainPackManifest | None:
        path = self._pack_path(pack_id)
        if not path.exists():
            return None
        return DomainPackManifest.from_dict(json.loads(path.read_text(encoding="utf-8")))

    def save_pack(self, manifest: DomainPackManifest) -> DomainPackManifest:
        manifest.updated_at = datetime.now(timezone.utc).isoformat()
        path = self._pack_path(manifest.id)
        path.write_text(json.dumps(manifest.to_dict(), indent=2), encoding="utf-8")
        index = self._read_index()
        index[manifest.domain_name] = manifest.id
        self._write_index(index)
        return manifest

    def create_pack(self, fields: dict[str, Any]) -> DomainPackManifest:
        pack_id = str(uuid.uuid4())
        manifest = DomainPackManifest(
            id=pack_id,
            domain_name=str(fields.get("domain_name") or fields.get("domain") or "new-domain"),
            version=str(fields.get("version") or "0.1.0"),
            jurisdictions=list(fields.get("jurisdictions") or []),
            glossary=[row for row in fields.get("glossary", []) if isinstance(row, dict)],
        )
        if fields.get("glossary"):
            from keprix.backend.domain_packs.schemas import GlossaryTerm

            manifest.glossary = [GlossaryTerm.from_dict(row) for row in fields["glossary"] if isinstance(row, dict)]
        return self.save_pack(manifest)

    def delete_pack(self, pack_id: str) -> bool:
        pack = self.get_pack(pack_id)
        if pack is None:
            return False
        path = self._pack_path(pack_id)
        if path.exists():
            path.unlink()
        index = self._read_index()
        index = {name: pid for name, pid in index.items() if pid != pack_id}
        self._write_index(index)
        return True


_store: DomainPackStore | None = None


def get_domain_pack_store() -> DomainPackStore:
    global _store
    if _store is None:
        _store = DomainPackStore()
    return _store


def reset_domain_pack_store(base_dir: Path | None = None) -> DomainPackStore:
    global _store
    _store = DomainPackStore(base_dir=base_dir)
    return _store
