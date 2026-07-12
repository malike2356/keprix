"""Import Agent OS client kit zip bundles."""

from __future__ import annotations

import json
import zipfile
from uuid import uuid4
from pathlib import Path
from typing import Any

from keprix_constants import get_keprix_home


class ClientKitImporter:
    def import_zip(self, path: str | Path) -> dict[str, Any]:
        source = Path(path)
        if not source.is_file():
            raise FileNotFoundError(f"Client kit not found: {source}")
        imported = {"pins": 0, "cron_jobs": 0, "playbooks": 0, "agent_apps": 0}
        with zipfile.ZipFile(source, "r") as zf:
            self._validate_names(zf)
            if "action-board.json" in zf.namelist():
                data = zf.read("action-board.json").decode("utf-8")
                target = get_keprix_home() / "agent-os" / "action-board.json"
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(data, encoding="utf-8")
                imported["pins"] = len((json.loads(data).get("pins") or []))
            for name in zf.namelist():
                if name.startswith("automations/cron/") and name.endswith(".json"):
                    job = json.loads(zf.read(name).decode("utf-8"))
                    self._append_cron_job(job)
                    imported["cron_jobs"] += 1
                elif name.startswith("automations/playbooks/") and name.endswith((".yaml", ".yml")):
                    target = get_keprix_home() / "playbooks" / "promoted" / Path(name).name
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(zf.read(name))
                    imported["playbooks"] += 1
                elif name.startswith("automations/agent-apps/") and not name.endswith("/"):
                    rel = Path(*Path(name).parts[2:])
                    target = get_keprix_home() / "agent-apps" / rel
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(zf.read(name))
                    if rel.name == "agent.yaml":
                        imported["agent_apps"] += 1
        return imported

    def _validate_names(self, zf: zipfile.ZipFile) -> None:
        for name in zf.namelist():
            path = Path(name)
            if path.is_absolute() or ".." in path.parts:
                raise ValueError(f"Unsafe client kit member: {name}")

    def _append_cron_job(self, job: dict[str, Any]) -> None:
        cron_dir = get_keprix_home() / "cron"
        cron_dir.mkdir(parents=True, exist_ok=True)
        jobs_path = cron_dir / "jobs.json"
        try:
            jobs = json.loads(jobs_path.read_text(encoding="utf-8")) if jobs_path.exists() else []
        except json.JSONDecodeError:
            jobs = []
        restored = dict(job)
        restored["id"] = uuid4().hex[:12]
        restored["origin"] = {"source": "client_kit_import", "original_id": job.get("id")}
        jobs.append(restored)
        jobs_path.write_text(json.dumps(jobs, indent=2), encoding="utf-8")
