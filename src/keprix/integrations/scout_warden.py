"""Optional Scout Warden client (disabled by default for CE)."""

from __future__ import annotations

import os
from typing import Any

import httpx


def scout_warden_enabled() -> bool:
    return os.environ.get("KEPRIX_SCOUT_WARDEN_ENABLED", "0").lower() in {"1", "true", "yes", "on"}


def scout_base_url() -> str:
    return (os.environ.get("KEPRIX_SCOUT_WARDEN_URL") or "").rstrip("/")


def scout_auth_header() -> dict[str, str]:
    token = os.environ.get("KEPRIX_SCOUT_WARDEN_TOKEN") or ""
    if not token:
        return {}
    return {"Authorization": f"Bearer {token}"}


class ScoutWardenClient:
    def __init__(
        self,
        *,
        base_url: str | None = None,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.base_url = (base_url or scout_base_url()).rstrip("/")
        self._transport = transport

    async def request_scan(self, *, target: str, tenant_id: str = "local") -> dict[str, Any]:
        if not scout_warden_enabled():
            return {"ok": False, "disabled": True, "reason": "KEPRIX_SCOUT_WARDEN_ENABLED=0"}
        if not self.base_url:
            return {"ok": False, "disabled": True, "reason": "KEPRIX_SCOUT_WARDEN_URL unset"}
        try:
            async with httpx.AsyncClient(transport=self._transport, timeout=15.0) as client:
                resp = await client.post(
                    f"{self.base_url}/v1/scans",
                    headers=scout_auth_header(),
                    json={"target": target, "tenant_id": tenant_id},
                )
                resp.raise_for_status()
                return {"ok": True, "scan": resp.json()}
        except Exception as exc:
            return {"ok": False, "error": str(exc), "degraded": True}

    async def get_status(self, scan_id: str) -> dict[str, Any]:
        if not scout_warden_enabled() or not self.base_url:
            return {"ok": False, "disabled": True}
        try:
            async with httpx.AsyncClient(transport=self._transport, timeout=15.0) as client:
                resp = await client.get(
                    f"{self.base_url}/v1/scans/{scan_id}",
                    headers=scout_auth_header(),
                )
                resp.raise_for_status()
                return {"ok": True, "scan": resp.json()}
        except Exception as exc:
            return {"ok": False, "error": str(exc), "degraded": True}

    def ingest_alert(self, alert: dict[str, Any]) -> dict[str, Any]:
        from datetime import datetime, timezone

        finding = {
            "id": alert.get("id") or alert.get("alert_id"),
            "severity": alert.get("severity") or "info",
            "title": alert.get("title") or "Scout alert",
            "summary": alert.get("summary") or alert.get("message") or "",
            "source": "scout_warden",
            "received_at": datetime.now(timezone.utc).isoformat(),
        }
        try:
            from keprix.security.scout_correlation import append_signal_event

            append_signal_event(
                {
                    "category": "scout_warden_alert",
                    "action": "ingest",
                    "severity": finding["severity"],
                    "title": finding["title"],
                    "details": finding,
                    "products": {"keprix": 1},
                }
            )
        except Exception as exc:
            finding["persist_error"] = str(exc)
        return {"ok": True, "finding": finding}
