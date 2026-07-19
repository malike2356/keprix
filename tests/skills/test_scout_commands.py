"""Tests for ScoutCommands safety layer."""

from __future__ import annotations

from keprix.skills.scout_commands import ScoutCommands


def test_freeze_blocks_writes():
    scout = ScoutCommands()
    scout.freeze()
    assert scout.should_block_write() is True


def test_guard_confirms_all():
    scout = ScoutCommands()
    scout.guard()
    assert scout.should_confirm("read_file") is True


def test_careful_confirms_writes_only():
    scout = ScoutCommands()
    scout.careful()
    assert scout.should_confirm("write_file") is True
    assert scout.should_confirm("read_file") is False


def test_unfreeze_resets():
    scout = ScoutCommands()
    scout.freeze()
    scout.guard()
    scout.unfreeze()
    assert scout.should_block_write() is False
    assert scout.should_confirm("write_file") is False
    assert scout.caution_level == "normal"


def test_status_line():
    scout = ScoutCommands()
    assert "caution=normal" in scout.status()
