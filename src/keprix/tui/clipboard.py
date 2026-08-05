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
    if _copy_with_pyperclip(payload):
        return True
    if _copy_with_platform_tools(payload):
        return True
    return osc52_copy(payload)


def _copy_with_pyperclip(payload: str) -> bool:
    try:
        import pyperclip

        pyperclip.copy(payload)
        return True
    except Exception:
        return False


def _copy_with_platform_tools(payload: str) -> bool:
    session = os.environ.get("XDG_SESSION_TYPE", "").lower()
    if session == "wayland" and shutil.which("wl-copy"):
        return _run_clipboard(["wl-copy"], payload)

    if shutil.which("xclip"):
        return _run_clipboard(["xclip", "-selection", "clipboard"], payload)

    if shutil.which("wl-copy"):
        return _run_clipboard(["wl-copy"], payload)

    if shutil.which("pbcopy"):
        return _run_clipboard(["pbcopy"], payload)

    return False


def _run_clipboard(command: list[str], payload: str) -> bool:
    result = subprocess.run(
        command,
        input=payload.encode("utf-8"),
        check=False,
        capture_output=True,
    )
    return result.returncode == 0


def osc52_copy(text: str) -> bool:
    import base64

    encoded = base64.b64encode(text.encode("utf-8")).decode("ascii")
    try:
        sys.stdout.write(f"\033]52;c;{encoded}\007")
        sys.stdout.flush()
        return True
    except Exception:
        return False
