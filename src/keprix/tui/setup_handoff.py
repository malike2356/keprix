"""Optional subprocess handoff to the canonical CLI setup wizard."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys


def run_setup_handoff(section: str = "") -> int:
    """Suspend the TUI and run ``keprix setup`` (or a section) in the foreground."""
    keprix_bin = shutil.which("keprix")
    if keprix_bin:
        cmd = [keprix_bin, "setup"]
    else:
        cmd = [sys.executable, "-m", "keprix_cli.main", "setup"]
    section = (section or "").strip()
    if section:
        cmd.append(section)
    env = os.environ.copy()
    env.pop("KEPRIX_SETUP_REQUIRED", None)
    return subprocess.call(cmd, env=env)
