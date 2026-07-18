"""Scout bridge to the Sentinel daemon. Commands over a Unix socket.

If the socket is missing, helpers return an error status gracefully (no raise).
"""

from __future__ import annotations

import json
import logging
import os
import socket
from typing import Any

logger = logging.getLogger(__name__)

SENTINEL_SOCKET = os.environ.get("SENTINEL_SOCKET", "/var/run/scout/sentinel.sock")


def socket_path() -> str:
    return os.environ.get("SENTINEL_SOCKET", SENTINEL_SOCKET)


def sentinel_available() -> bool:
    """True when the Sentinel Unix socket exists on disk."""
    return os.path.exists(socket_path())


def _send_command(cmd: dict[str, Any], *, timeout: float = 2.0) -> dict[str, Any]:
    """Send a command to Sentinel; return response or error dict."""
    path = socket_path()
    if not os.path.exists(path):
        return {"status": "error", "reason": "sentinel not running"}

    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        sock.settimeout(timeout)
        sock.connect(path)
        sock.sendall(json.dumps(cmd).encode("utf-8"))
        data = sock.recv(65536)
        if not data:
            return {"status": "error", "reason": "empty response"}
        return json.loads(data.decode("utf-8"))
    except OSError as exc:
        logger.warning("sentinel command failed: %s", exc)
        return {"status": "error", "reason": str(exc)}
    except json.JSONDecodeError as exc:
        return {"status": "error", "reason": f"invalid response: {exc}"}
    finally:
        try:
            sock.close()
        except OSError:
            pass


def sentinel_block_egress() -> bool:
    """Block agent network egress at iptables level (via Sentinel)."""
    resp = _send_command({"action": "block_egress"})
    return resp.get("status") == "ok"


def sentinel_unblock_egress() -> bool:
    """Remove agent egress block."""
    resp = _send_command({"action": "unblock_egress"})
    return resp.get("status") == "ok"


def sentinel_block_ip(ip: str) -> bool:
    """Block a specific IP for the agent."""
    resp = _send_command({"action": "block_ip", "ip": ip})
    return resp.get("status") == "ok"


def sentinel_kill_agent(pid: int) -> bool:
    """Ask Sentinel to kill the agent process tree (daemon may still dry-run)."""
    resp = _send_command({"action": "kill_agent", "pid": pid})
    return resp.get("status") == "ok"


def sentinel_protect_files() -> bool:
    """Make Scout security files immutable (via Sentinel)."""
    resp = _send_command({"action": "protect_files"})
    return resp.get("status") == "ok"


def sentinel_verify_integrity() -> dict[str, Any]:
    """Check protected file presence / integrity via Sentinel."""
    return _send_command({"action": "verify_integrity"})


def sentinel_health_check() -> dict[str, Any]:
    """Check if Sentinel is alive and enforcing."""
    return _send_command({"action": "health_check"})


def sentinel_apply_cgroup_limits(pid: int) -> bool:
    """Apply cgroup resource limits to agent."""
    resp = _send_command({"action": "cgroup_limits", "pid": pid})
    return resp.get("status") == "ok"


def ensure_sentinel_health(*, required: bool | None = None) -> dict[str, Any]:
    """Health probe used by Scout.

    If Sentinel is required (SENTINEL_REQUIRED=1) and health fails, force Python
    egress block via scout_control. Otherwise soft-warn.
    """
    from keprix.security.scout_control import set_egress_force_blocked

    if required is None:
        required = os.environ.get("SENTINEL_REQUIRED", "0").strip() == "1"

    if not sentinel_available():
        result = {
            "status": "error",
            "reason": "sentinel not running",
            "required": required,
        }
        if required:
            set_egress_force_blocked(True)
            result["fallback"] = "egress_force_blocked"
            logger.error("Sentinel required but unavailable; forced egress block")
        else:
            logger.warning("Sentinel socket missing; continuing without kernel enforcement")
        return result

    health = sentinel_health_check()
    if health.get("status") != "ok" or not health.get("healthy", False):
        result = {
            "status": "error",
            "reason": health.get("reason", "health_check_failed"),
            "required": required,
            "health": health,
        }
        if required:
            set_egress_force_blocked(True)
            result["fallback"] = "egress_force_blocked"
            logger.error("Sentinel health failed; forced egress block")
        else:
            logger.warning("Sentinel health failed: %s", health)
        return result

    return {"status": "ok", "required": required, "health": health}
