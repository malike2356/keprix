#!/usr/bin/env python3
"""Sentinel Daemon: Unix socket listener for Scout enforcement commands.

Default is dry-run (SENTINEL_ENFORCE unset/0). Does not chattr the whole carina tree.
"""

from __future__ import annotations

import json
import logging
import os
import socket
import sys
import threading
from typing import Any

from keprix.security.sentinel.file_guard import protect_all, verify_integrity
from keprix.security.sentinel.firewall_guard import (
    apply_egress_block,
    block_ip,
    is_egress_blocked,
    unblock_all,
)
from keprix.security.sentinel.process_guard import (
    apply_cgroup_limits,
    kill_agent_tree,
    monitor_agent_heartbeat,
)

logger = logging.getLogger(__name__)

SOCKET_PATH = os.environ.get("SENTINEL_SOCKET", "/var/run/scout/sentinel.sock")
COMMAND_PIPE = os.environ.get("SENTINEL_COMMAND_PIPE", "/var/run/scout/sentinel/commands")
PROTECT_ON_START = os.environ.get("SENTINEL_PROTECT_ON_START", "0").strip() == "1"


def handle_command(cmd: dict[str, Any]) -> dict[str, Any]:
    """Process a command from Scout."""
    action = cmd.get("action")

    if action == "block_egress":
        result = apply_egress_block()
        return {"status": result.get("status", "ok"), "action": "block_egress", **result}

    if action == "unblock_egress":
        result = unblock_all()
        return {"status": result.get("status", "ok"), "action": "unblock_egress", **result}

    if action == "block_ip":
        ip = cmd.get("ip")
        if not ip:
            return {"status": "error", "reason": "missing ip"}
        result = block_ip(str(ip))
        return {"status": result.get("status", "ok"), "action": "block_ip", **result}

    if action == "protect_files":
        result = protect_all()
        return {"status": result.get("status", "ok"), "action": "protect_files", **result}

    if action == "verify_integrity":
        result = verify_integrity()
        return {"status": "ok", "action": "verify_integrity", "result": result}

    if action == "kill_agent":
        pid = cmd.get("pid")
        if pid is None:
            return {"status": "error", "reason": "missing pid"}
        result = kill_agent_tree(int(pid))
        return {"status": result.get("status", "ok"), "action": "kill_agent", **result}

    if action == "cgroup_limits":
        pid = cmd.get("pid")
        if pid is None:
            return {"status": "error", "reason": "missing pid"}
        result = apply_cgroup_limits(int(pid))
        return {"status": result.get("status", "ok"), "action": "cgroup_limits", **result}

    if action == "health_check":
        integrity = verify_integrity()
        return {
            "status": "ok",
            "healthy": True,
            "egress_blocked": is_egress_blocked(),
            "enforce": os.environ.get("SENTINEL_ENFORCE", "0") == "1",
            "integrity": integrity,
        }

    return {"status": "error", "reason": f"unknown action: {action}"}


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    agent_pid = int(args[0]) if args else None

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s sentinel %(levelname)s %(message)s",
    )

    if PROTECT_ON_START:
        protect_all()

    if agent_pid:
        apply_cgroup_limits(agent_pid)
        heartbeat_thread = threading.Thread(
            target=monitor_agent_heartbeat,
            args=(agent_pid, COMMAND_PIPE),
            daemon=True,
        )
        heartbeat_thread.start()

    if os.path.exists(SOCKET_PATH):
        os.unlink(SOCKET_PATH)
    os.makedirs(os.path.dirname(SOCKET_PATH), exist_ok=True)
    os.makedirs(os.path.dirname(COMMAND_PIPE), exist_ok=True)

    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(SOCKET_PATH)
    os.chmod(SOCKET_PATH, 0o660)
    server.listen(5)
    logger.info(
        "listening on %s enforce=%s",
        SOCKET_PATH,
        os.environ.get("SENTINEL_ENFORCE", "0"),
    )

    try:
        while True:
            conn, _ = server.accept()
            try:
                data = conn.recv(65536)
                if not data:
                    continue
                try:
                    cmd = json.loads(data.decode("utf-8"))
                except json.JSONDecodeError as exc:
                    response = {"status": "error", "reason": f"invalid json: {exc}"}
                else:
                    response = handle_command(cmd)
                conn.sendall(json.dumps(response).encode("utf-8"))
            except Exception as exc:
                logger.exception("command handling failed")
                try:
                    conn.sendall(
                        json.dumps({"status": "error", "reason": str(exc)}).encode("utf-8")
                    )
                except OSError:
                    pass
            finally:
                try:
                    conn.close()
                except OSError:
                    pass
    except KeyboardInterrupt:
        logger.info("shutdown")
    finally:
        try:
            server.close()
        except OSError:
            pass
        if os.path.exists(SOCKET_PATH):
            try:
                os.unlink(SOCKET_PATH)
            except OSError:
                pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
