"""Capacity and headroom checks."""

from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from keprix_cli.config import get_keprix_home


def capacity_report() -> dict[str, Any]:
    home = Path(get_keprix_home())
    usage = shutil.disk_usage(home)
    free_gb = round(usage.free / (1024**3), 2)
    total_gb = round(usage.total / (1024**3), 2)
    scout_metrics = home / "scout" / "product_metrics.json"
    forensics = home / "forensics" / "snapshots"
    snapshot_count = len(list(forensics.glob("ckpt-*.json"))) if forensics.exists() else 0
    warnings: list[str] = []
    if free_gb < 5:
        warnings.append("Disk free space below 5GB")
    if snapshot_count > 200:
        warnings.append("Forensic snapshot count is high; archive old snapshots")
    return {
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "disk_free_gb": free_gb,
        "disk_total_gb": total_gb,
        "keprix_home": str(home),
        "scout_metrics_present": scout_metrics.exists(),
        "forensic_snapshots": snapshot_count,
        "warnings": warnings,
        "ok": not warnings,
    }
