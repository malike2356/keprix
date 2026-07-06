"""Cross-plane export helpers."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any


def export_dataset_copy(source: Path, dest_dir: Path, *, fmt: str) -> dict[str, Any]:
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{source.stem}.{fmt.lstrip('.')}"
    shutil.copy2(source, dest)
    return {"path": str(dest), "format": fmt, "bytes": dest.stat().st_size}


def export_metadata_bundle(payload: dict[str, Any], dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return dest
