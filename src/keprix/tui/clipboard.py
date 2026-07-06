"""Best-effort clipboard helpers for the terminal UI."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys


def copy_text(text: str) -> bool:
    payload = text.strip()
    if not payload:
        return False
    try:
        import pyperclip

        pyperclip.copy(payload)
        return True
    except Exception:
        pass

    session = os.environ.get("XDG_SESSION_TYPE", "").lower()
    if session == "wayland" and shutil.which("wl-copy"):
        result = subprocess.run(
            ["wl-copy"],
            input=payload.encode("utf-8"),
            check=False,
            capture_output=True,
        )
        return result.returncode == 0

    if shutil.which("xclip"):
        result = subprocess.run(
            ["xclip", "-selection", "clipboard"],
            input=payload.encode("utf-8"),
            check=False,
            capture_output=True,
        )
        return result.returncode == 0

    if shutil.which("wl-copy"):
        result = subprocess.run(
            ["wl-copy"],
            input=payload.encode("utf-8"),
            check=False,
            capture_output=True,
        )
        return result.returncode == 0

    if shutil.which("pbcopy"):
        result = subprocess.run(
            ["pbcopy"],
            input=payload.encode("utf-8"),
            check=False,
            capture_output=True,
        )
        return result.returncode == 0

    # OSC 52 works over SSH when clipboard tools are unavailable.
    if _osc52_copy(payload):
        return True
    return False


def _osc52_copy(text: str) -> bool:
    import base64

    encoded = base64.b64encode(text.encode("utf-8")).decode("ascii")
    try:
        sys.stdout.write(f"\033]52;c;{encoded}\007")
        sys.stdout.flush()
        return True
    except Exception:
        return False
