"""Dataset manager orchestration."""

from __future__ import annotations

import json
import re
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from keprix.research_workspace.datasets.codebook import Codebook
from keprix.research_workspace.datasets.export import export_dataset
from keprix.research_workspace.datasets.importers import import_research_dataset, read_preview_rows
from keprix.research_workspace.datasets.lineage import LineageStore
from keprix.research_workspace.datasets.transforms import apply_transform
from keprix.research_workspace.datasets.validation import validate_sample
from keprix.research_workspace.datasets.variables import build_variables_from_columns
from keprix.research_workspace.schemas import new_trace_id

_EMAIL_RE = re.compile(r"[^@]+@[^@]+\.[^@]+")


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _redact_preview_value(value: Any) -> Any:
    if value is None:
        return None
    text = str(value)
    if _EMAIL_RE.search(text):
        return "[redacted-email]"
    if len(text) > 48:
        return text[:24] + "...[redacted]"
    return value


class DatasetManager:
    def __init__(self, store: Any) -> None:
        self.store = store
        self.root = store.plane.root / "datasets"
        self.originals_dir = self.root / "originals"
        self.derived_dir = self.root / "derived"
        self.codebooks_dir = self.root / "codebooks"
        self.exports_dir = self.root / "exports"
        self.lineage = LineageStore(self.root / "lineage")
        for path in (self.originals_dir, self.derived_dir, self.codebooks_dir, self.exports_dir):
            path.mkdir(parents=True, exist_ok=True)

    def import_file(
        self,
        project_id: str,
        *,
        source_path: Path,
        name: str,
        owner: str,
        sqlite_table: str | None = None,
    ) -> dict[str, Any]:
        dataset_id = f"ds-{uuid.uuid4().hex[:10]}"
        version_number = 1
        version_id = f"{dataset_id}-v{version_number}"
        dataset_dir = self.derived_dir / dataset_id / f"v{version_number}"
        dataset_dir.mkdir(parents=True, exist_ok=True)

        originals_path = self.originals_dir / dataset_id
        meta = import_research_dataset(
            source_path,
            originals_dir=originals_path,
            sqlite_table=sqlite_table,
        )
        derived_csv = dataset_dir / "data.csv"
        if source_path.suffix.lower() in {".csv", ".tsv"}:
            shutil.copy2(source_path, derived_csv)
        elif source_path.suffix.lower() == ".json":
            converted = source_path.with_suffix(".converted.csv")
            if converted.exists():
                shutil.copy2(converted, derived_csv)
        elif meta.get("source_format") not in {"pspp_syntax"}:
            converted = source_path.with_suffix(".converted.csv")
            if converted.exists():
                shutil.copy2(converted, derived_csv)
            elif source_path.suffix.lower() in {".csv", ".tsv"}:
                shutil.copy2(source_path, derived_csv)

        columns, rows = read_preview_rows(derived_csv, limit=1000) if derived_csv.exists() else ([], [])
        variables = build_variables_from_columns(
            columns,
            rows,
            labels=meta.get("variable_labels") or {},
            value_labels=meta.get("value_labels") or {},
        )
        codebook = Codebook(dataset_id=dataset_id, version_id=version_id, variables=variables)
        self._save_codebook(codebook)

        trace_id = new_trace_id()
        self.lineage.append_step(dataset_id, version_number, "import", source=str(source_path), meta=meta)
        self.store.plane.register_dataset_version(
            dataset_id=dataset_id,
            name=name,
            fmt=source_path.suffix.lstrip(".") or "csv",
            path=str(derived_csv if derived_csv.exists() else originals_path),
            db_path=meta.get("db_path"),
            engine=meta.get("engine"),
            row_count=meta.get("row_count"),
            lineage={"steps": self.lineage.load(dataset_id, version_number).to_dict()["steps"]},
        )
        object_row = self.store.save_object(
            object_id=dataset_id,
            object_type="dataset",
            project_id=project_id,
            owner=owner,
            source_ref=str(originals_path),
            provenance={"original_path": meta.get("original_path"), "import_meta": meta},
            payload={
                "name": name,
                "format": source_path.suffix.lstrip(".") or "csv",
                "path": str(derived_csv if derived_csv.exists() else originals_path),
                "version_id": version_id,
                "version_number": version_number,
                "row_count": meta.get("row_count"),
                "project_id": project_id,
            },
            trace_id=trace_id,
        )
        self.store.save_object(
            object_id=f"cb-{dataset_id}",
            object_type="codebook",
            project_id=project_id,
            owner=owner,
            source_ref=str(self._codebook_path(dataset_id, version_number)),
            provenance={"dataset_id": dataset_id},
            payload=codebook.to_dict(),
            trace_id=trace_id,
        )
        return {
            "dataset_id": dataset_id,
            "version_id": version_id,
            "version_number": version_number,
            "codebook": codebook.to_dict(),
            "meta": meta,
            "object": object_row,
        }

    def get_dataset(self, dataset_id: str) -> dict[str, Any] | None:
        with self.store.plane.connect() as conn:
            row = conn.execute(
                "SELECT * FROM research_objects WHERE object_id = ? AND object_type = 'dataset'",
                (dataset_id,),
            ).fetchone()
        if not row:
            return None
        item = dict(row)
        payload = json.loads(item["payload_json"] or "{}")
        version_number = int(payload.get("version_number") or 1)
        codebook = self.load_codebook(dataset_id, version_number)
        lineage = self.lineage.load(dataset_id, version_number)
        return {
            "dataset_id": dataset_id,
            "project_id": item["project_id"],
            "payload": payload,
            "codebook": codebook.to_dict() if codebook else None,
            "lineage": lineage.to_dict(),
        }

    def load_codebook(self, dataset_id: str, version_number: int) -> Codebook | None:
        path = self._codebook_path(dataset_id, version_number)
        if not path.exists():
            return None
        return Codebook.from_dict(json.loads(path.read_text(encoding="utf-8")))

    def save_codebook(self, codebook: Codebook) -> Codebook:
        self._save_codebook(codebook)
        version_number = int(codebook.version_id.rsplit("v", maxsplit=1)[-1])
        self.lineage.append_step(codebook.dataset_id, version_number, "codebook_update")
        return codebook

    def preview(self, dataset_id: str, *, limit: int = 5) -> dict[str, Any]:
        dataset = self.get_dataset(dataset_id)
        if dataset is None:
            raise ValueError("Dataset not found")
        path = Path(dataset["payload"]["path"])
        columns, rows = read_preview_rows(path, limit=limit)
        redacted = [
            {key: _redact_preview_value(value) for key, value in row.items()}
            for row in rows
        ]
        return {"dataset_id": dataset_id, "columns": columns, "rows": redacted, "preview_limit": limit}

    def transform(
        self,
        dataset_id: str,
        *,
        transform: str,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        current = self.get_dataset(dataset_id)
        if current is None:
            raise ValueError("Dataset not found")
        version_number = int(current["payload"].get("version_number") or 1) + 1
        version_id = f"{dataset_id}-v{version_number}"
        source_csv = Path(current["payload"]["path"])
        dest_dir = self.derived_dir / dataset_id / f"v{version_number}"
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_csv = dest_dir / "data.csv"
        codebook = self.load_codebook(dataset_id, version_number - 1)
        if codebook is None:
            raise ValueError("Codebook not found")
        previous_lineage = self.lineage.load(dataset_id, version_number - 1)
        new_lineage = self.lineage.load(dataset_id, version_number)
        new_lineage.steps = list(previous_lineage.steps)
        self.lineage.save(new_lineage)
        codebook.version_id = version_id
        updated = apply_transform(
            source_csv=source_csv,
            dest_csv=dest_csv,
            codebook=codebook,
            transform=transform,
            params=params,
            dataset_id=dataset_id,
            version_number=version_number,
            lineage_store=self.lineage,
        )
        self._save_codebook(updated)
        current["payload"]["path"] = str(dest_csv)
        current["payload"]["version_number"] = version_number
        current["payload"]["version_id"] = version_id
        self.store.save_object(
            object_id=dataset_id,
            object_type="dataset",
            project_id=current["project_id"],
            owner="system",
            source_ref=str(dest_csv),
            provenance={"transform": transform},
            payload=current["payload"],
            trace_id=new_trace_id(),
        )
        return {"dataset_id": dataset_id, "version_id": version_id, "codebook": updated.to_dict()}

    def export(self, dataset_id: str, *, fmt: str) -> dict[str, Any]:
        dataset = self.get_dataset(dataset_id)
        if dataset is None:
            raise ValueError("Dataset not found")
        version_number = int(dataset["payload"].get("version_number") or 1)
        codebook = self.load_codebook(dataset_id, version_number)
        if codebook is None:
            raise ValueError("Codebook not found")
        path = Path(dataset["payload"]["path"])
        out_dir = self.exports_dir / dataset_id / f"v{version_number}"
        return export_dataset(data_path=path, codebook=codebook, fmt=fmt, dest_dir=out_dir)  # type: ignore[arg-type]

    def validate(self, dataset_id: str, *, sample_size: int = 50) -> dict[str, Any]:
        dataset = self.get_dataset(dataset_id)
        if dataset is None:
            raise ValueError("Dataset not found")
        version_number = int(dataset["payload"].get("version_number") or 1)
        codebook = self.load_codebook(dataset_id, version_number)
        if codebook is None:
            raise ValueError("Codebook not found")
        _, rows = read_preview_rows(Path(dataset["payload"]["path"]), limit=sample_size)
        return validate_sample(rows, codebook)

    def _codebook_path(self, dataset_id: str, version_number: int) -> Path:
        return self.codebooks_dir / dataset_id / f"v{version_number}.json"

    def _save_codebook(self, codebook: Codebook) -> None:
        version_number = int(codebook.version_id.rsplit("v", maxsplit=1)[-1])
        path = self._codebook_path(codebook.dataset_id, version_number)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(codebook.to_dict(), indent=2), encoding="utf-8")
