"""Resolve KEPRIX_HOME for standalone skill scripts.

Skill scripts may run outside the Keprix process (e.g. system Python,
nix env, CI) where ``keprix_constants`` is not importable.  This module
provides the same ``get_keprix_home()`` and ``display_keprix_home()``
contracts as ``keprix_constants`` without requiring it on ``sys.path``.

When ``keprix_constants`` IS available it is used directly so that any
future enhancements (profile resolution, Docker detection, etc.) are
picked up automatically.  The fallback path replicates the core logic
from ``keprix_constants.py`` using only the stdlib.

All scripts under ``google-workspace/scripts/`` should import from here
instead of duplicating the ``KEPRIX_HOME = Path(os.getenv(...))`` pattern.
"""

from __future__ import annotations

import os
from pathlib import Path

try:
    from keprix_constants import display_keprix_home as display_keprix_home
    from keprix_constants import get_keprix_home as get_keprix_home
except (ModuleNotFoundError, ImportError):

    def get_keprix_home() -> Path:
        """Return the Keprix home directory (default: ~/.keprix).

        Mirrors ``keprix_constants.get_keprix_home()``."""
        val = os.environ.get("KEPRIX_HOME", "").strip()
        return Path(val) if val else Path.home() / ".keprix"

    def display_keprix_home() -> str:
        """Return a user-friendly ``~/``-shortened display string.

        Mirrors ``keprix_constants.display_keprix_home()``."""
        home = get_keprix_home()
        try:
            return "~/" + str(home.relative_to(Path.home()))
        except ValueError:
            return str(home)
