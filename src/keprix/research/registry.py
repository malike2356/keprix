"""Persistent research task registry (survives restarts)."""

from __future__ import annotations

import json
import re
import secrets
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

TASK_ID_RE = re.compile(r"^rsch-[a-z0-9]{8}$")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _research_dir() -> Path:
    try:
        from keprix_cli.config import get_keprix_home

        root = Path(get_keprix_home()) / "research"
    except Exception:
        root = Path.home() / ".keprix" / "research"
    root.mkdir(parents=True, exist_ok=True)
    return root


@dataclass
class ResearchTaskRecord:
    id: str
    workspace_id: str
    user_id: str
    query: str
    depth: str
    status: str = "pending"
    model: str | None = None
    progress_pct: int = 0
    current_step: str | None = None
    result_markdown: str | None = None
    result_document_id: str | None = None
    error_message: str | None = None
    sub_questions: list[str] = field(default_factory=list)
    sources: list[dict[str, Any]] = field(default_factory=list)
    tokens_used: int = 0
    created_at: str = field(default_factory=lambda: _utcnow().isoformat())
    started_at: str | None = None
    completed_at: str | None = None
    cancelled_at: str | None = None
    expires_at: str = field(
        default_factory=lambda: (_utcnow() + timedelta(days=30)).isoformat(),
    )

    def to_dict(self, *, include_report: bool = True) -> dict[str, Any]:
        payload = asdict(self)
        if not include_report:
            payload.pop("result_markdown", None)
        payload["job_id"] = self.id
        payload["model_used"] = self.model
        return payload


class ResearchTaskRegistry:
    def __init__(self, base_dir: Path | None = None) -> None:
        self._dir = base_dir or _research_dir()
        self._tasks_path = self._dir / "tasks.json"
        self._events_path = self._dir / "events.jsonl"
        self._tasks: dict[str, ResearchTaskRecord] = {}
        self._event_seq = 0
        self._load()

    def _load(self) -> None:
        if self._tasks_path.exists():
            rows = json.loads(self._tasks_path.read_text(encoding="utf-8"))
            for row in rows:
                task = ResearchTaskRecord(**row)
                self._tasks[task.id] = task
        if self._events_path.exists():
            for line in self._events_path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                event = json.loads(line)
                self._event_seq = max(self._event_seq, int(event.get("id", 0)))

    def _save_tasks(self) -> None:
        rows = [asdict(task) for task in self._tasks.values()]
        self._tasks_path.write_text(json.dumps(rows, indent=2), encoding="utf-8")

    def generate_id(self) -> str:
        return "rsch-" + secrets.token_hex(4)

    def create(
        self,
        *,
        workspace_id: str,
        user_id: str,
        query: str,
        depth: str,
        model: str | None = None,
    ) -> ResearchTaskRecord:
        task_id = self.generate_id()
        while task_id in self._tasks:
            task_id = self.generate_id()
        task = ResearchTaskRecord(
            id=task_id,
            workspace_id=workspace_id,
            user_id=user_id,
            query=query,
            depth=depth,
            model=model,
            status="running",
            started_at=_utcnow().isoformat(),
        )
        self._tasks[task_id] = task
        self._save_tasks()
        self.append_event(task_id, "step_start", {"step": "queued"})
        return task

    def get(self, task_id: str, user_id: str | None = None) -> ResearchTaskRecord | None:
        if not TASK_ID_RE.fullmatch(task_id):
            return None
        task = self._tasks.get(task_id)
        if task is None:
            return None
        if user_id is not None and task.user_id != user_id:
            return None
        return task

    def list_for_user(self, user_id: str) -> list[ResearchTaskRecord]:
        tasks = [t for t in self._tasks.values() if t.user_id == user_id]
        tasks.sort(key=lambda t: t.created_at, reverse=True)
        return tasks

    def update(self, task: ResearchTaskRecord) -> None:
        self._tasks[task.id] = task
        self._save_tasks()

    def cancel(self, task_id: str, user_id: str) -> bool:
        task = self.get(task_id, user_id)
        if task is None:
            return False
        task.status = "cancelled"
        task.cancelled_at = _utcnow().isoformat()
        self.update(task)
        self.append_event(task_id, "cancelled", {})
        return True

    def delete(self, task_id: str, user_id: str) -> bool:
        task = self.get(task_id, user_id)
        if task is None:
            return False
        self._tasks.pop(task_id, None)
        self._save_tasks()
        return True

    def append_event(self, task_id: str, event_type: str, payload: dict[str, Any]) -> int:
        self._event_seq += 1
        row = {
            "id": self._event_seq,
            "task_id": task_id,
            "event_type": event_type,
            "payload": payload,
            "emitted_at": _utcnow().isoformat(),
        }
        with self._events_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row) + "\n")
        return self._event_seq

    def list_events(self, task_id: str, *, since_id: int = 0) -> list[dict[str, Any]]:
        if not self._events_path.exists():
            return []
        events: list[dict[str, Any]] = []
        for line in self._events_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            event = json.loads(line)
            if event.get("task_id") != task_id:
                continue
            if int(event.get("id", 0)) <= since_id:
                continue
            events.append(event)
        return events

    def purge_expired(self) -> int:
        now = _utcnow()
        removed = 0
        for task_id, task in list(self._tasks.items()):
            try:
                expires = datetime.fromisoformat(task.expires_at)
            except ValueError:
                continue
            if expires.tzinfo is None:
                expires = expires.replace(tzinfo=timezone.utc)
            if expires < now:
                self._tasks.pop(task_id, None)
                removed += 1
        if removed:
            self._save_tasks()
        return removed


_registry: ResearchTaskRegistry | None = None


def get_research_registry() -> ResearchTaskRegistry:
    global _registry
    if _registry is None:
        _registry = ResearchTaskRegistry()
    return _registry
