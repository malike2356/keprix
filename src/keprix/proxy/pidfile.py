"""PID file helpers for background proxy process."""

from __future__ import annotations

import os
import signal
from pathlib import Path

from keprix.proxy.paths import proxy_pid_path


def write_pid(pid: int | None = None) -> Path:
    path = proxy_pid_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(str(pid or os.getpid()), encoding="utf-8")
    return path


def read_pid() -> int | None:
    path = proxy_pid_path()
    if not path.is_file():
        return None
    try:
        return int(path.read_text(encoding="utf-8").strip())
    except ValueError:
        return None


def is_running() -> bool:
    pid = read_pid()
    if pid is None:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def stop_running() -> bool:
    pid = read_pid()
    if pid is None:
        return False
    try:
        os.kill(pid, signal.SIGTERM)
    except OSError:
        proxy_pid_path().unlink(missing_ok=True)
        return False
    proxy_pid_path().unlink(missing_ok=True)
    return True
