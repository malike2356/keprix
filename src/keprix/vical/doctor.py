"""Operator-facing viCal / Zoom doctor summary (Prompt 632)."""

from __future__ import annotations

import os
from typing import Any

from keprix.vical.conferencing import sync_notes
from keprix.vical.zoom_oauth import is_zoom_oauth_configured, zoom_connection_status


def run_vical_doctor(*, workspace_id: str = "default", user_id: str = "default") -> dict[str, Any]:
    zoom = zoom_connection_status(workspace_id, user_id)
    return {
        "ok": True,
        "vicalEnabled": os.environ.get("KEPRIX_VICAL_ENABLED", "1").strip().lower()
        not in {"0", "false", "no", "off"},
        "canonicalService": "keprix.vical.saga.book_with_saga",
        "zoomOAuthConfigured": is_zoom_oauth_configured(),
        "zoom": {
            "status": zoom.get("status"),
            "connected": zoom.get("connected"),
            "accountEmail": zoom.get("accountEmail"),
            "scopes": zoom.get("scopes"),
            "standalone": True,
            "verloxCredentialServiceRequired": False,
        },
        "webhook": {
            "path": "/api/vical/webhooks/zoom",
            "secretConfigured": bool(
                (os.environ.get("KEPRIX_CONCIERGE_ZOOM_WEBHOOK_SECRET") or "").strip()
                or (os.environ.get("ZOOM_WEBHOOK_SECRET") or "").strip()
            ),
            "googleCalendarPath": "/api/vical/webhooks/google-calendar",
            "googleCalendarTokenConfigured": bool(
                (os.environ.get("KEPRIX_CONCIERGE_GOOGLE_CALENDAR_WEBHOOK_TOKEN") or "").strip()
            ),
        },
        "calendar": {
            "googleAdapter": True,
            "microsoftAdapter": True,
            "icsFallback": True,
            "durableOutbox": True,
            "invitationEvidenceSeparateFromHostEvent": True,
        },
        "fallback": {
            "staticRoomUrl": True,
            "ics": True,
            "claimsManagedZoom": False,
        },
        "conferencing": sync_notes(),
        "failures": [
            tip
            for tip, cond in [
                ("Set ZOOM_CLIENT_ID and ZOOM_CLIENT_SECRET for managed Zoom", not is_zoom_oauth_configured()),
                ("Connect Zoom host via /api/customer-concierge/integrations/zoom/connect", not zoom.get("connected")),
                (
                    "Set KEPRIX_CONCIERGE_ZOOM_WEBHOOK_SECRET for signed webhooks",
                    not (
                        (os.environ.get("KEPRIX_CONCIERGE_ZOOM_WEBHOOK_SECRET") or "").strip()
                        or (os.environ.get("ZOOM_WEBHOOK_SECRET") or "").strip()
                    ),
                ),
            ]
            if cond
        ],
    }


__all__ = ["run_vical_doctor"]
