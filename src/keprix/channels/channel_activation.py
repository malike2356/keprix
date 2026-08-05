"""Post-configure activation: reload env and request gateway adapter refresh."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from keprix.proxy.paths import keprix_home


def _utcnow() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def reload_request_path() -> Path:
    return keprix_home() / "channel_reload_request.json"


def gateway_pid_path() -> Path:
    return keprix_home() / "gateway.pid"


def reload_dotenv_into_process() -> bool:
    """Pull ~/.keprix/.env into os.environ for the current process."""
    try:
        from keprix_cli.env_loader import load_keprix_dotenv

        load_keprix_dotenv(keprix_home=keprix_home())
        return True
    except Exception:
        # Fallback: already upserted into os.environ by channel_config_store
        return False


def gateway_appears_running() -> bool:
    path = gateway_pid_path()
    if not path.is_file():
        return False
    try:
        pid = int(path.read_text(encoding="utf-8").strip().splitlines()[0])
    except (OSError, ValueError):
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def request_channel_reload(channel_id: str, *, env_keys: list[str] | None = None) -> dict[str, Any]:
    """Reload dotenv and write a reload marker for a running gateway.

    Full adapter hot-start is not always possible; when a gateway PID is live
    we ask the operator (via tool message) to restart or `/platform resume`.
    """
    dotenv_reloaded = reload_dotenv_into_process()
    running = gateway_appears_running()
    payload = {
        "channel_id": channel_id,
        "requested_at": _utcnow(),
        "env_keys": env_keys or [],
        "gateway_running": running,
    }
    path = reload_request_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    try:
        path.chmod(0o600)
    except OSError:
        pass

    if running:
        hint = (
            "Credentials are in ~/.keprix/.env. Gateway looks running; "
            "restart the gateway (or `/platform resume <name>` if paused) "
            "so the adapter reconnects."
        )
        requires_restart = True
    else:
        hint = (
            "Credentials are in ~/.keprix/.env and this process. "
            "Start the gateway when ready; no separate dashboard step needed."
        )
        requires_restart = False

    return {
        "dotenv_reloaded": dotenv_reloaded,
        "gateway_running": running,
        "requires_restart": requires_restart,
        "restart_hint": hint,
        "reload_request_path": str(path),
    }
