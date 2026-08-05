"""Discover first-party domain packs on disk."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def domain_packs_root() -> Path:
    # filesystem.py -> domain_packs -> backend -> keprix -> src -> project root
    return Path(__file__).resolve().parents[4] / "domain-packs"


def list_filesystem_packs() -> list[dict[str, Any]]:
    root = domain_packs_root()
    if not root.is_dir():
        return []
    out: list[dict[str, Any]] = []
    for path in sorted(root.iterdir()):
        if not path.is_dir() or path.name.startswith("_"):
            continue
        manifest = path / "pack.json"
        if not manifest.exists():
            continue
        try:
            data = json.loads(manifest.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        data = dict(data)
        data.setdefault("id", f"fs:{path.name}")
        data["source"] = "filesystem"
        data["path"] = str(path)
        out.append(data)
    return out
