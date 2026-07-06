"""Dataset catalog for the analytical data plane."""

from __future__ import annotations

import json
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _data_dir() -> Path:
    try:
        from keprix_cli.config import get_keprix_home

        root = Path(get_keprix_home()) / "data_plane"
    except Exception:
        root = Path.home() / ".keprix" / "data_plane"
    root.mkdir(parents=True, exist_ok=True)
    return root


class DatasetCatalog:
    def __init__(self, base_dir: Path | None = None) -> None:
        self._root = base_dir or _data_dir()
        self._datasets_dir = self._root / "datasets"
        self._datasets_dir.mkdir(parents=True, exist_ok=True)
        self._index_path = self._root / "catalog.json"
        self._datasets: list[dict[str, Any]] = []
        if self._index_path.exists():
            self._datasets = json.loads(self._index_path.read_text(encoding="utf-8"))

    def _save(self) -> None:
        self._index_path.write_text(json.dumps(self._datasets, indent=2), encoding="utf-8")

    def list(self) -> list[dict[str, Any]]:
        return list(self._datasets)

    def get(self, dataset_id: str) -> dict[str, Any] | None:
        for row in self._datasets:
            if row.get("id") == dataset_id:
                return row
        return None

    def register(
        self,
        *,
        name: str,
        source_path: Path,
        format: str,
        row_count: int | None = None,
        db_path: str | None = None,
        engine: str | None = None,
    ) -> dict[str, Any]:
        dataset_id = "ds-" + secrets.token_hex(4)
        dest = self._datasets_dir / f"{dataset_id}{source_path.suffix}"
        dest.write_bytes(source_path.read_bytes())
        row = {
            "id": dataset_id,
            "name": name,
            "format": format,
            "path": str(dest),
            "db_path": db_path,
            "engine": engine,
            "row_count": row_count,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self._datasets.append(row)
        self._save()
        return row

    def remove(self, dataset_id: str) -> bool:
        row = self.get(dataset_id)
        if row is None:
            return False
        Path(row["path"]).unlink(missing_ok=True)
        self._datasets = [d for d in self._datasets if d.get("id") != dataset_id]
        self._save()
        return True


_catalog: DatasetCatalog | None = None


def get_dataset_catalog() -> DatasetCatalog:
    global _catalog
    if _catalog is None:
        _catalog = DatasetCatalog()
    return _catalog
