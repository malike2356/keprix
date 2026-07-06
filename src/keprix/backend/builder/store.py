"""Builder persistence (Prompt 29)."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _builder_dir() -> Path:
    import os

    base = os.environ.get("KEPRIX_DATA_DIR", "").strip()
    if base:
        root = Path(base) / "builder"
    else:
        try:
            from keprix_cli.config import get_keprix_home

            root = Path(get_keprix_home()) / "builder"
        except Exception:
            root = Path.home() / ".keprix" / "builder"
    root.mkdir(parents=True, exist_ok=True)
    return root


class BuilderStore:
    def __init__(self, base_dir: Path | None = None) -> None:
        self._dir = base_dir or _builder_dir()
        self._projects_path = self._dir / "projects.json"
        self._jobs_path = self._dir / "jobs.jsonl"
        self._log_dir = self._dir / "logs"
        self._log_dir.mkdir(parents=True, exist_ok=True)

    def _read_projects(self) -> dict[str, Any]:
        if not self._projects_path.exists():
            return {}
        return json.loads(self._projects_path.read_text(encoding="utf-8"))

    def _write_projects(self, data: dict[str, Any]) -> None:
        self._projects_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def upsert_project(self, fields: dict[str, Any]) -> dict[str, Any]:
        data = self._read_projects()
        incoming_id = fields.get("id")
        project_id = str(incoming_id) if incoming_id else str(uuid.uuid4())
        existing = data.get(project_id, {})
        if not incoming_id:
            by_path = self.get_project_by_path(str(fields.get("path", "")))
            if by_path:
                project_id = str(by_path["id"])
                existing = data.get(project_id, by_path)
        clean_fields = {key: value for key, value in fields.items() if key != "id" or value is not None}
        row = {
            "id": project_id,
            "created_at": existing.get("created_at") or datetime.now(timezone.utc).isoformat(),
            **existing,
            **clean_fields,
            "last_scanned_at": datetime.now(timezone.utc).isoformat(),
        }
        data[project_id] = row
        self._write_projects(data)
        return row

    def list_projects(self) -> list[dict[str, Any]]:
        return sorted(self._read_projects().values(), key=lambda row: row.get("name", ""))

    def get_project(self, project_id: str) -> dict[str, Any] | None:
        return self._read_projects().get(project_id)

    def get_project_by_path(self, path: str) -> dict[str, Any] | None:
        normalized = str(Path(path).resolve())
        for row in self.list_projects():
            if str(Path(row.get("path", "")).resolve()) == normalized:
                return row
        return None

    def create_job(self, fields: dict[str, Any]) -> dict[str, Any]:
        row = {
            "id": str(uuid.uuid4()),
            "status": "pending",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "output": "",
            **fields,
        }
        with self._jobs_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row) + "\n")
        return row

    def _read_jobs(self) -> list[dict[str, Any]]:
        if not self._jobs_path.exists():
            return []
        return [
            json.loads(line)
            for line in self._jobs_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    def _write_jobs(self, rows: list[dict[str, Any]]) -> None:
        self._jobs_path.write_text(
            "\n".join(json.dumps(row) for row in rows) + ("\n" if rows else ""),
            encoding="utf-8",
        )

    def update_job(self, job_id: str, patch: dict[str, Any]) -> dict[str, Any] | None:
        rows = self._read_jobs()
        updated = None
        for row in rows:
            if row.get("id") == job_id:
                row.update(patch)
                updated = row
        if updated:
            self._write_jobs(rows)
        return updated

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        for row in self._read_jobs():
            if row.get("id") == job_id:
                return row
        return None

    def list_jobs(self, *, project_id: str | None = None) -> list[dict[str, Any]]:
        rows = self._read_jobs()
        if project_id:
            rows = [row for row in rows if row.get("project_id") == project_id]
        return sorted(rows, key=lambda row: row.get("created_at", ""), reverse=True)

    def append_job_log(self, job_id: str, line: str) -> None:
        path = self._log_dir / f"{job_id}.log"
        with path.open("a", encoding="utf-8") as handle:
            handle.write(line.rstrip() + "\n")
        job = self.get_job(job_id)
        if job:
            self.update_job(job_id, {"output": (job.get("output") or "") + line.rstrip() + "\n"})

    def read_job_log(self, job_id: str) -> str:
        path = self._log_dir / f"{job_id}.log"
        if path.exists():
            return path.read_text(encoding="utf-8")
        job = self.get_job(job_id)
        return str(job.get("output") or "") if job else ""


_store: BuilderStore | None = None


def get_builder_store() -> BuilderStore:
    global _store
    if _store is None:
        _store = BuilderStore()
    return _store


def reset_builder_store() -> None:
    global _store
    _store = None
