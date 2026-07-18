"""Sentinel: kernel / OS-level enforcement companion for Scout.

Default mode is dry-run. Real iptables/chattr actions require SENTINEL_ENFORCE=1.
Agent kill via Sentinel requires SENTINEL_ALLOW_KILL=1 (default off).
"""

from __future__ import annotations

__all__ = [
    "enforce_enabled",
    "allow_kill_enabled",
]

import os


def enforce_enabled() -> bool:
    """True only when real OS enforcement is explicitly enabled."""
    return os.environ.get("SENTINEL_ENFORCE", "0").strip() == "1"


def allow_kill_enabled() -> bool:
    """True only when Sentinel may SIGKILL agent processes."""
    return os.environ.get("SENTINEL_ALLOW_KILL", "0").strip() == "1"
