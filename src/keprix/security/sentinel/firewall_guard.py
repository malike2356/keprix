"""Sentinel Firewall Guard: iptables helpers for agent egress.

All mutating calls are NO-OP unless SENTINEL_ENFORCE=1.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import time
from typing import Any

from keprix.security.sentinel import enforce_enabled

logger = logging.getLogger(__name__)

SCOUT_UID = int(os.environ.get("SENTINEL_AGENT_UID", "1001"))
STATE_DIR = os.environ.get("SENTINEL_STATE_DIR", "/var/run/scout/sentinel")
BLOCKLIST_FILE = os.path.join(STATE_DIR, "egress_blocklist.json")
WHITELIST_FILE = os.path.join(STATE_DIR, "egress_whitelist.json")


def _run_iptables(args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["iptables", *args],
        check=check,
        capture_output=True,
        text=True,
    )


def _ensure_state_dir() -> None:
    os.makedirs(STATE_DIR, exist_ok=True)


def apply_egress_block() -> dict[str, Any]:
    """Block all outbound traffic from the agent UID. Whitelist bypasses."""
    if not enforce_enabled():
        logger.info("firewall_guard dry-run: apply_egress_block uid=%s", SCOUT_UID)
        return {"status": "ok", "dry_run": True, "action": "block_egress", "uid": SCOUT_UID}

    _ensure_state_dir()
    _run_iptables(
        ["-A", "OUTPUT", "-m", "owner", "--uid-owner", str(SCOUT_UID), "-j", "DROP"],
        check=True,
    )
    if os.path.exists(WHITELIST_FILE):
        with open(WHITELIST_FILE, encoding="utf-8") as handle:
            whitelist = json.load(handle)
        for entry in whitelist:
            ip = entry.get("ip")
            if not ip:
                continue
            _run_iptables(
                [
                    "-I",
                    "OUTPUT",
                    "1",
                    "-m",
                    "owner",
                    "--uid-owner",
                    str(SCOUT_UID),
                    "-d",
                    ip,
                    "-j",
                    "ACCEPT",
                ],
                check=True,
            )
    return {"status": "ok", "dry_run": False, "action": "block_egress", "uid": SCOUT_UID}


def block_ip(ip: str) -> dict[str, Any]:
    """Block a specific IP for the agent user."""
    if not enforce_enabled():
        logger.info("firewall_guard dry-run: block_ip %s uid=%s", ip, SCOUT_UID)
        return {"status": "ok", "dry_run": True, "action": "block_ip", "ip": ip}

    _ensure_state_dir()
    _run_iptables(
        [
            "-I",
            "OUTPUT",
            "1",
            "-m",
            "owner",
            "--uid-owner",
            str(SCOUT_UID),
            "-d",
            ip,
            "-j",
            "DROP",
        ],
        check=True,
    )
    blocklist: list[dict[str, Any]] = []
    if os.path.exists(BLOCKLIST_FILE):
        with open(BLOCKLIST_FILE, encoding="utf-8") as handle:
            blocklist = json.load(handle)
    blocklist.append({"ip": ip, "timestamp": time.time()})
    with open(BLOCKLIST_FILE, "w", encoding="utf-8") as handle:
        json.dump(blocklist, handle)
    return {"status": "ok", "dry_run": False, "action": "block_ip", "ip": ip}


def unblock_all() -> dict[str, Any]:
    """Remove agent-specific DROP rule (best-effort)."""
    if not enforce_enabled():
        logger.info("firewall_guard dry-run: unblock_all uid=%s", SCOUT_UID)
        return {"status": "ok", "dry_run": True, "action": "unblock_egress"}

    _run_iptables(
        ["-D", "OUTPUT", "-m", "owner", "--uid-owner", str(SCOUT_UID), "-j", "DROP"],
        check=False,
    )
    return {"status": "ok", "dry_run": False, "action": "unblock_egress"}


def is_egress_blocked() -> bool:
    """Check if the agent egress DROP rule is present."""
    if not enforce_enabled():
        return False
    result = _run_iptables(
        ["-C", "OUTPUT", "-m", "owner", "--uid-owner", str(SCOUT_UID), "-j", "DROP"],
        check=False,
    )
    return result.returncode == 0
