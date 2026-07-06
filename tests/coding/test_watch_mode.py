"""Tests for watch mode debounce behavior."""

from __future__ import annotations

import time
from pathlib import Path

from keprix.coding.watch_mode import WatchSession


def test_watch_mode_detects_changes_without_loop(tmp_path: Path) -> None:
    repo = tmp_path
    (repo / "app.py").write_text("v1\n", encoding="utf-8")
    session = WatchSession(repo_path=repo, debounce_seconds=0.0)
    session.resume()
    assert session.scan_once() == []

    time.sleep(0.02)
    (repo / "app.py").write_text("v2\n", encoding="utf-8")
    events = session.scan_once()
    assert len(events) == 1
    assert events[0].path == "app.py"
    assert events[0].event_type == "modified"

    # Same snapshot should not re-emit until another change.
    assert session.scan_once() == []

    session.pause()
    (repo / "app.py").write_text("v3\n", encoding="utf-8")
    assert session.scan_once() == []


def test_watch_mode_ignores_keprix_paths(tmp_path: Path) -> None:
    repo = tmp_path
    keprix_dir = repo / ".keprix" / "workspace"
    keprix_dir.mkdir(parents=True)
    (keprix_dir / "state.json").write_text("{}", encoding="utf-8")
    session = WatchSession(repo_path=repo, debounce_seconds=0.0)
    session.resume()
    assert session.scan_once() == []
