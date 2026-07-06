"""File watch mode for coding sessions without infinite loops."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class WatchEvent:
    path: str
    event_type: str
    mtime: float


@dataclass
class WatchSession:
    repo_path: Path
    debounce_seconds: float = 1.0
    ignore_prefixes: tuple[str, ...] = (
        ".git/",
        "node_modules/",
        ".venv/",
        "__pycache__/",
        ".keprix/",
        "coding-trajectories/",
    )
    _snapshots: dict[str, float] = field(default_factory=dict, init=False)
    _last_emit: float = field(default=0.0, init=False)
    _paused: bool = field(default=False, init=False)

    def pause(self) -> None:
        self._paused = True

    def resume(self) -> None:
        self._paused = False
        self._snapshots = self._scan()

    def scan_once(self) -> list[WatchEvent]:
        if self._paused:
            return []
        now = time.monotonic()
        if now - self._last_emit < self.debounce_seconds:
            return []

        current = self._scan()
        events: list[WatchEvent] = []
        all_paths = set(current) | set(self._snapshots)
        for rel in sorted(all_paths):
            old_mtime = self._snapshots.get(rel)
            new_mtime = current.get(rel)
            if old_mtime is None and new_mtime is not None:
                events.append(WatchEvent(path=rel, event_type="created", mtime=new_mtime))
            elif old_mtime is not None and new_mtime is None:
                events.append(WatchEvent(path=rel, event_type="deleted", mtime=0.0))
            elif old_mtime != new_mtime and new_mtime is not None:
                events.append(WatchEvent(path=rel, event_type="modified", mtime=new_mtime))

        if events:
            self._snapshots = current
            self._last_emit = now
        return events

    def _scan(self) -> dict[str, float]:
        root = self.repo_path.resolve()
        snapshot: dict[str, float] = {}
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            rel = str(path.relative_to(root)).replace("\\", "/")
            if self._ignored(rel):
                continue
            try:
                snapshot[rel] = path.stat().st_mtime
            except OSError:
                continue
        return snapshot

    def _ignored(self, rel: str) -> bool:
        return any(rel.startswith(prefix) or f"/{prefix}" in f"/{rel}" for prefix in self.ignore_prefixes)
