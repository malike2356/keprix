"""Fleet manager tests."""

from __future__ import annotations

from pathlib import Path

from keprix.fleet.manager import FleetManager


def test_register_and_health(tmp_path: Path) -> None:
    manager = FleetManager(base_dir=tmp_path)
    row = manager.register(name="prod-1", base_url="https://keprix.example.test", version="2.1.0")
    updated = manager.record_health(row["id"], metrics={"cpu_pct": 95, "ram_pct": 40, "disk_pct": 20})
    assert updated
    assert updated["status"] == "degraded"
    assert manager.list_audit()
