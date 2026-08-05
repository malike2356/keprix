"""Tests for upgrade/history.py."""

from __future__ import annotations

from pathlib import Path

from keprix.upgrade.history import append_history, get_last_record, load_history
from keprix.upgrade.models import UpgradeRecord


def test_load_history_missing_file_returns_empty(tmp_path: Path):
    path = tmp_path / "history.json"
    assert load_history(path) == []


def test_load_history_invalid_json_returns_empty(tmp_path: Path):
    path = tmp_path / "history.json"
    path.write_text("not json", encoding="utf-8")
    assert load_history(path) == []


def test_append_and_load_round_trip(tmp_path: Path):
    path = tmp_path / "upgrade" / "history.json"
    record = UpgradeRecord(
        from_version="0.3.0",
        to_version="0.7.0",
        timestamp="2026-07-02T14:30:00",
        backup_path="/tmp/backup",
        status="success",
        duration_seconds=9.1,
    )
    append_history(record, path)
    loaded = load_history(path)
    assert len(loaded) == 1
    assert loaded[0].from_version == "0.3.0"
    assert loaded[0].to_version == "0.7.0"
    assert loaded[0].status == "success"
    assert loaded[0].duration_seconds == 9.1


def test_append_preserves_existing_records(tmp_path: Path):
    path = tmp_path / "history.json"
    first = UpgradeRecord("0.1.0", "0.2.0", "t1", "/b1", "success")
    second = UpgradeRecord("0.2.0", "0.3.0", "t2", "/b2", "success")
    append_history(first, path)
    append_history(second, path)
    loaded = load_history(path)
    assert len(loaded) == 2
    assert loaded[0].from_version == "0.1.0"
    assert loaded[1].from_version == "0.2.0"


def test_get_last_record(tmp_path: Path):
    path = tmp_path / "history.json"
    assert get_last_record(path) is None
    append_history(UpgradeRecord("0.1.0", "0.2.0", "t1", "/b1", "success"), path)
    append_history(UpgradeRecord("0.2.0", "0.3.0", "t2", "/b2", "success"), path)
    last = get_last_record(path)
    assert last is not None
    assert last.to_version == "0.3.0"
