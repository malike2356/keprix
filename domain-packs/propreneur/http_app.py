"""Minimal ASGI health app for the Propreneur domain pack."""

from __future__ import annotations

import json
from pathlib import Path

from tools.registry import list_tool_names, load_tools_contract


async def app(scope, receive, send):  # type: ignore[no-untyped-def]
    if scope["type"] != "http":
        return
    path = scope.get("path") or "/"
    if path in {"/", "/health"}:
        body = json.dumps({"ok": True, "product": "propreneur", "status": "live"}).encode()
        status = 200
    elif path == "/propreneur/capabilities":
        contract = load_tools_contract()
        body = json.dumps(
            {
                "product": "propreneur",
                "contract_version": contract["version"],
                "tools": list_tool_names(),
            }
        ).encode()
        status = 200
    else:
        body = json.dumps({"error": "not_found"}).encode()
        status = 404
    await send(
        {
            "type": "http.response.start",
            "status": status,
            "headers": [[b"content-type", b"application/json"]],
        }
    )
    await send({"type": "http.response.body", "body": body})


PACK_ROOT = Path(__file__).resolve().parent
