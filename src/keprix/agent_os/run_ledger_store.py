"""File-backed Agent OS run ledger store with workspace JSON exports."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from keprix.agent_os.run_ledger import LoopProfile, RunLedgerEntry
from keprix.workspace.template_presets import workspace_root
from keprix_constants import get_keprix_home


def _store_root() -> Path:
    root = get_keprix_home() / "agent-os" / "run-ledger"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _entries_dir() -> Path:
    path = _store_root() / "entries"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _profiles_dir() -> Path:
    path = _store_root() / "profiles"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _profile_filename(source_type: str, source_id: str) -> str:
    safe = "".join(ch if ch.isalnum() or ch in {"-", "_", "."} else "-" for ch in f"{source_type}-{source_id}")
    return f"{safe}.json"


class RunLedgerStore:
    def add(self, entry: RunLedgerEntry) -> RunLedgerEntry:
        (_entries_dir() / f"{entry.entry_id}.json").write_text(json.dumps(entry.to_dict(), indent=2), encoding="utf-8")
        self.export_to_workspace(entry)
        return entry

    def get(self, entry_id: str) -> RunLedgerEntry | None:
        path = _entries_dir() / f"{entry_id}.json"
        if not path.exists():
            return None
        return RunLedgerEntry(**json.loads(path.read_text(encoding="utf-8")))

    def get_by_run(self, run_id: str) -> RunLedgerEntry | None:
        for entry in self.list(limit=500):
            if entry.run_id == run_id:
                return entry
        return None

    def list(
        self,
        *,
        source_type: str | None = None,
        source_id: str | None = None,
        workspace_id: str | None = None,
        status: str | None = None,
        limit: int = 100,
    ) -> list[RunLedgerEntry]:
        entries: list[RunLedgerEntry] = []
        for path in _entries_dir().glob("*.json"):
            data = json.loads(path.read_text(encoding="utf-8"))
            if source_type and data.get("source_type") != source_type:
                continue
            if source_id and data.get("source_id") != source_id:
                continue
            if workspace_id and data.get("workspace_id") != workspace_id:
                continue
            if status and data.get("status") != status:
                continue
            entries.append(RunLedgerEntry(**data))
        entries.sort(key=lambda item: item.created_at, reverse=True)
        return entries[: max(1, min(limit, 500))]

    def save_profile(self, profile: LoopProfile) -> LoopProfile:
        path = _profiles_dir() / _profile_filename(profile.source_type, profile.source_id)
        path.write_text(json.dumps(profile.to_dict(), indent=2), encoding="utf-8")
        return profile

    def get_profile(self, source_type: str, source_id: str) -> LoopProfile | None:
        path = _profiles_dir() / _profile_filename(source_type, source_id)
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        return LoopProfile(
            source_type=str(data["source_type"]),
            source_id=str(data["source_id"]),
            baseline_entry_ids=list(data.get("baseline_entry_ids") or []),
            improvement_proposals=list(data.get("improvement_proposals") or []),
        )

    def export_to_workspace(self, entry: RunLedgerEntry) -> Path | None:
        if not entry.workspace_id or entry.workspace_id == "default":
            return None
        root = workspace_root(entry.workspace_id)
        if not root.exists():
            return None
        runs_dir = root / "runs"
        runs_dir.mkdir(parents=True, exist_ok=True)
        path = runs_dir / f"{entry.entry_id}.json"
        path.write_text(json.dumps(entry.to_dict(), indent=2), encoding="utf-8")
        return path

    def write_draft(self, proposal_id: str, filename: str, content: str) -> Path:
        drafts = get_keprix_home() / "agent-os" / "loop-profile-drafts" / proposal_id
        drafts.mkdir(parents=True, exist_ok=True)
        path = drafts / filename
        path.write_text(content, encoding="utf-8")
        return path
