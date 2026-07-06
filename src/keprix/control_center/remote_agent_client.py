"""Remote agent server HTTP client."""

from __future__ import annotations

from typing import Any

import httpx

from keprix.control_center.agent_server_registry import resolve_server_token


async def ping_health(server: dict[str, Any], owner: str) -> dict[str, Any]:
    url = server["url"].rstrip("/")
    token = await resolve_server_token(server["id"], owner)
    headers: dict[str, str] = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{url}/api/health", headers=headers)
            if response.status_code == 200:
                return {"ok": True, "status": "healthy", "detail": response.json()}
            return {"ok": False, "status": "degraded", "detail": {"status_code": response.status_code}}
    except Exception as exc:
        if url.startswith("http://127.0.0.1") or "localhost" in url:
            return {"ok": True, "status": "local", "detail": {"message": "Local server assumed healthy"}}
        return {"ok": False, "status": "unreachable", "detail": {"error": str(exc)}}
