"""Tests for stale-safe hash-anchored edits."""

from pathlib import Path

from keprix.coding.scoped_replace import (
    apply_edit,
    hash_anchor,
    replace_hashed_block,
    rollback_edit,
)


def test_hash_anchor_is_stable() -> None:
    assert hash_anchor("return 1") == hash_anchor("return 1")
    assert hash_anchor("return 1") != hash_anchor("return 2")


def test_hashed_replace_applies_and_rolls_back(tmp_path: Path) -> None:
    target = tmp_path / "sample.py"
    target.write_text("def value():\n    return 1\n", encoding="utf-8")
    old_block = "return 1"

    result = replace_hashed_block(tmp_path, "sample.py", hash_anchor(old_block), old_block, "return 2")
    assert result.ok
    apply_edit(result, tmp_path)
    assert "return 2" in target.read_text(encoding="utf-8")
    rollback_edit(result, tmp_path)
    assert "return 1" in target.read_text(encoding="utf-8")


def test_hashed_replace_rejects_stale_anchor_without_writing(tmp_path: Path) -> None:
    target = tmp_path / "sample.py"
    target.write_text("def value():\n    return 9\n", encoding="utf-8")
    old_block = "return 1"

    result = replace_hashed_block(tmp_path, "sample.py", hash_anchor(old_block), old_block, "return 2")
    assert not result.ok
    assert "stale anchor" in (result.error or "").lower()
    assert "return 9" in (result.error or "")
    assert target.read_text(encoding="utf-8") == "def value():\n    return 9\n"
