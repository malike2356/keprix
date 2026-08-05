"""CLI handlers for ``keprix channel-shield``."""

from __future__ import annotations

import asyncio
import json


def _run(coro):
    return asyncio.run(coro)


def cmd_channel_shield(args) -> int:
    command = args.channel_shield_command
    as_json = bool(getattr(args, "json", False))

    if command == "doctor":
        from keprix.channel_shield.doctor import run_doctor

        payload = _run(run_doctor())
    elif command == "adapters":
        from keprix.channel_shield.adapters.registry import adapters_health, list_adapters

        payload = {"adapters": list_adapters(), "health": _run(adapters_health())}
    elif command == "e2e":
        from keprix.channel_shield.doctor import run_e2e, run_e2e_matrix

        channel = getattr(args, "channel", "all") or "all"
        if getattr(args, "channel_shield_alias", None) == "email":
            channel = "email"
        if channel == "all":
            payload = _run(run_e2e_matrix())
        else:
            payload = _run(run_e2e(channel))
    else:
        payload = {"ok": False, "error": f"unknown command: {command}"}
        print(json.dumps(payload, indent=2) if as_json else payload["error"])
        return 1

    if as_json:
        print(json.dumps(payload, indent=2, default=str))
    else:
        ok = payload.get("ok", True)
        print(json.dumps(payload, indent=2, default=str))
        return 0 if ok else 1
    return 0 if payload.get("ok", True) else 1
