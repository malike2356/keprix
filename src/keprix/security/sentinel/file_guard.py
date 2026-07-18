"""Sentinel File Guard: chattr helpers for Scout security modules.

Default protect set is ONLY keprix Scout security Python files under
keprix/src/keprix/security/*.py (selected modules). NEVER the entire carina/ tree.

Mutating calls are NO-OP unless SENTINEL_ENFORCE=1.
"""

from __future__ import annotations

import logging
import os
import subprocess
from pathlib import Path
from typing import Any

from keprix.security.sentinel import enforce_enabled

logger = logging.getLogger(__name__)

_SECURITY_DIR = Path(__file__).resolve().parents[1]

# Explicit allowlist only. Do not walk carina/ or other product trees.
_DEFAULT_PROTECTED = (
    "scout_control.py",
    "scout_listener.py",
    "auto_response.py",
    "sentinel_client.py",
    "egress_gate.py",
    "egress_policy.py",
    "network_gate.py",
)

_GOVERNANCE_KILL_RELAY = (
    Path(__file__).resolve().parents[2] / "governance" / "kill_relay.py"
)


def protected_paths() -> list[str]:
    """Resolve the default protect set (files that exist)."""
    paths: list[str] = []
    for name in _DEFAULT_PROTECTED:
        candidate = _SECURITY_DIR / name
        if candidate.is_file():
            paths.append(str(candidate))
    if _GOVERNANCE_KILL_RELAY.is_file():
        paths.append(str(_GOVERNANCE_KILL_RELAY))
    extra = os.environ.get("SENTINEL_EXTRA_PROTECT", "").strip()
    if extra:
        for item in extra.split(":"):
            item = item.strip()
            if item and os.path.isfile(item):
                # Refuse broad directory protection of carina trees.
                if "/carina/" in item and not item.endswith(".py"):
                    logger.warning("refusing SENTINEL_EXTRA_PROTECT path: %s", item)
                    continue
                paths.append(item)
    return paths


def make_immutable(path: str) -> dict[str, Any]:
    """chattr +i when enforcement is on; otherwise dry-run log."""
    if not enforce_enabled():
        logger.info("file_guard dry-run: chattr +i %s", path)
        return {"status": "ok", "dry_run": True, "path": path, "action": "immutable"}
    subprocess.run(["chattr", "+i", path], check=True, capture_output=True, text=True)
    return {"status": "ok", "dry_run": False, "path": path, "action": "immutable"}


def make_mutable(path: str) -> dict[str, Any]:
    """chattr -i when enforcement is on; otherwise dry-run log."""
    if not enforce_enabled():
        logger.info("file_guard dry-run: chattr -i %s", path)
        return {"status": "ok", "dry_run": True, "path": path, "action": "mutable"}
    subprocess.run(["chattr", "-i", path], check=True, capture_output=True, text=True)
    return {"status": "ok", "dry_run": False, "path": path, "action": "mutable"}


def protect_all() -> dict[str, Any]:
    """Make default Scout security files immutable (or dry-run)."""
    results: list[dict[str, Any]] = []
    for path in protected_paths():
        try:
            results.append(make_immutable(path))
        except Exception as exc:
            results.append({"status": "error", "path": path, "reason": str(exc)})
    return {
        "status": "ok",
        "dry_run": not enforce_enabled(),
        "action": "protect_files",
        "count": len(results),
        "results": results,
    }


def unprotect_all() -> dict[str, Any]:
    """Remove immutability from the default protect set (or dry-run)."""
    results: list[dict[str, Any]] = []
    for path in protected_paths():
        try:
            results.append(make_mutable(path))
        except Exception as exc:
            results.append({"status": "error", "path": path, "reason": str(exc)})
    return {
        "status": "ok",
        "dry_run": not enforce_enabled(),
        "action": "unprotect_files",
        "count": len(results),
        "results": results,
    }


def verify_integrity() -> dict[str, Any]:
    """Report whether protected files exist and are readable."""
    missing: list[str] = []
    present: list[str] = []
    for path in protected_paths():
        if os.path.isfile(path) and os.access(path, os.R_OK):
            present.append(path)
        else:
            missing.append(path)
    return {
        "present": present,
        "missing": missing,
        "count_present": len(present),
        "count_missing": len(missing),
        "ok": len(missing) == 0,
    }
