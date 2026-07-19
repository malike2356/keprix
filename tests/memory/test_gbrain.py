"""Tests for GBrain memory store."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from keprix.memory.gbrain import GBrain


def test_save_and_query():
    gb = GBrain(":memory:")
    gb.save("keprix", "nexus", "decision", "Approved feature X for v0.4")
    results = gb.query("keprix", "nexus", {"type": "decision", "limit": 5})
    assert "Approved feature X" in results


def test_search():
    gb = GBrain(":memory:")
    gb.save("keprix", "warden", "incident", "SQL injection found in login form")
    gb.save("keprix", "warden", "incident", "XSS in comment field")
    results = gb.search("keprix", "SQL injection")
    assert len(results) >= 1
    assert "login form" in results[0]["content"]


def test_get_recent():
    gb = GBrain(":memory:")
    gb.save("keprix", "sage", "retro", "Shipped gstack routing")
    recent = gb.get_recent("keprix", "sage", days=7)
    assert "Shipped gstack routing" in recent


def test_old_entries_excluded_by_default():
    gb = GBrain(":memory:")
    gb.save("keprix", "nexus", "decision", "Old decision")
    # Backdate the row
    old = (datetime.now(timezone.utc) - timedelta(days=120)).isoformat()
    gb._conn.execute("UPDATE memories SET updated_at = ?, created_at = ?", (old, old))
    gb._conn.commit()
    results = gb.query("keprix", "nexus", {"type": "decision", "limit": 5})
    assert "Old decision" not in results
    results_old = gb.query(
        "keprix", "nexus", {"type": "decision", "limit": 5, "include_old": True}
    )
    assert "Old decision" in results_old
