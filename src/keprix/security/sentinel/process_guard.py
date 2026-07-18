"""Sentinel Process Guard: cgroup helpers and agent kill.

cgroup operations soft-fail when the hierarchy is unavailable.
Kill actions require SENTINEL_ALLOW_KILL=1 AND SENTINEL_ENFORCE=1.
"""

from __future__ import annotations

import logging
import os
import signal
import time
from typing import Any

from keprix.security.sentinel import allow_kill_enabled, enforce_enabled

logger = logging.getLogger(__name__)

SCOUT_UID = int(os.environ.get("SENTINEL_AGENT_UID", "1001"))
MAX_CHILDREN = int(os.environ.get("SENTINEL_MAX_CHILDREN", "50"))
MAX_MEMORY_MB = int(os.environ.get("SENTINEL_MAX_MEMORY_MB", "4096"))
CGROUP_ROOT = os.environ.get("SENTINEL_CGROUP_ROOT", "/sys/fs/cgroup/scout")


def apply_cgroup_limits(agent_pid: int) -> dict[str, Any]:
    """Put agent in a cgroup with hard resource limits (soft-fail)."""
    if not enforce_enabled():
        logger.info("process_guard dry-run: cgroup_limits pid=%s", agent_pid)
        return {
            "status": "ok",
            "dry_run": True,
            "action": "cgroup_limits",
            "pid": agent_pid,
        }

    cgroup_path = f"{CGROUP_ROOT}/agent-{agent_pid}"
    try:
        os.makedirs(cgroup_path, exist_ok=True)
        with open(f"{cgroup_path}/memory.max", "w", encoding="utf-8") as handle:
            handle.write(str(MAX_MEMORY_MB * 1024 * 1024))
        with open(f"{cgroup_path}/pids.max", "w", encoding="utf-8") as handle:
            handle.write(str(MAX_CHILDREN))
        with open(f"{cgroup_path}/cpu.max", "w", encoding="utf-8") as handle:
            handle.write("50000 100000")
        with open(f"{cgroup_path}/cgroup.procs", "w", encoding="utf-8") as handle:
            handle.write(str(agent_pid))
    except OSError as exc:
        logger.warning("cgroup unavailable or failed: %s", exc)
        return {
            "status": "error",
            "action": "cgroup_limits",
            "pid": agent_pid,
            "reason": f"cgroup_unavailable: {exc}",
            "soft_fail": True,
        }
    return {
        "status": "ok",
        "dry_run": False,
        "action": "cgroup_limits",
        "pid": agent_pid,
        "path": cgroup_path,
    }


def kill_agent_tree(agent_pid: int) -> dict[str, Any]:
    """Kill agent process and same-UID children when kill is allowed."""
    if not allow_kill_enabled() or not enforce_enabled():
        logger.info(
            "process_guard dry-run/denied: kill_agent pid=%s allow_kill=%s enforce=%s",
            agent_pid,
            allow_kill_enabled(),
            enforce_enabled(),
        )
        return {
            "status": "ok",
            "dry_run": True,
            "action": "kill_agent",
            "pid": agent_pid,
            "allowed": False,
        }

    killed: list[int] = []
    try:
        os.kill(agent_pid, signal.SIGKILL)
        killed.append(agent_pid)
    except ProcessLookupError:
        pass
    except PermissionError as exc:
        return {
            "status": "error",
            "action": "kill_agent",
            "pid": agent_pid,
            "reason": str(exc),
        }

    try:
        for entry in os.listdir("/proc"):
            if not entry.isdigit():
                continue
            pid = int(entry)
            try:
                with open(f"/proc/{pid}/status", encoding="utf-8") as handle:
                    for line in handle:
                        if line.startswith("Uid:"):
                            uid = int(line.split()[1])
                            if uid == SCOUT_UID:
                                try:
                                    os.kill(pid, signal.SIGKILL)
                                    killed.append(pid)
                                except (ProcessLookupError, PermissionError):
                                    pass
                            break
            except OSError:
                continue
    except OSError as exc:
        logger.warning("proc scan failed: %s", exc)

    return {
        "status": "ok",
        "dry_run": False,
        "action": "kill_agent",
        "pid": agent_pid,
        "killed": sorted(set(killed)),
    }


def monitor_agent_heartbeat(agent_pid: int, socket_path: str, *, timeout_seconds: float = 30.0) -> None:
    """If agent stops responding / process gone, optionally kill (when allowed)."""
    last_beat = time.time()
    while True:
        time.sleep(5)
        try:
            os.kill(agent_pid, 0)
        except ProcessLookupError:
            return
        except PermissionError:
            pass

        if os.path.exists(socket_path):
            try:
                stat = os.stat(socket_path)
                if stat.st_mtime > last_beat:
                    last_beat = stat.st_mtime
                    continue
            except OSError:
                pass

        if time.time() - last_beat > timeout_seconds:
            kill_agent_tree(agent_pid)
            return
