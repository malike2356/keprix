"""Tests for trajectory logging."""

from __future__ import annotations

from pathlib import Path

from keprix.coding.trajectory import TrajectoryLogger


def test_trajectory_redacts_secrets(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        "keprix.coding.trajectory._trajectory_dir",
        lambda: tmp_path,
    )
    logger = TrajectoryLogger()
    logger.log("test_event", {"token": "sk-abcdefghijklmnopqrstuvwxyz1234567890"})
    events = logger.read_events()
    assert events
    payload = events[0]["payload"]["token"]
    assert "sk-" not in payload
    assert "REDACTED" in payload


def test_trajectory_jsonl_append(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        "keprix.coding.trajectory._trajectory_dir",
        lambda: tmp_path,
    )
    logger = TrajectoryLogger()
    logger.log("start", {"issue": "fix bug"})
    logger.log("end", {"ok": True})
    assert len(logger.read_events()) == 2
    assert logger.path is not None
    assert logger.path.name.endswith(".jsonl")
