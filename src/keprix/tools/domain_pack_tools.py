"""Import domain-pack tool registrations into the tool registry."""

from __future__ import annotations

import importlib.util
from pathlib import Path


def _load(path: Path) -> None:
    if not path.exists():
        return
    spec = importlib.util.spec_from_file_location(f"domain_pack_{path.parent.name}_register", path)
    if spec is None or spec.loader is None:
        return
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)


_root = Path(__file__).resolve().parents[3] / "domain-packs"
_load(_root / "research-intel" / "tools" / "register.py")
_load(_root / "scheduling-ops" / "tools" / "register.py")
