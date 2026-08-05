"""Conversational integration configuration service."""

from __future__ import annotations

import os
from typing import Any

from keprix.channels.sensitive_scrub import sensitive_field_warning
from keprix.configure.integration_requirements import (
    find_integration,
    get_integration,
    list_integration_summaries,
)

_SESSIONS: dict[str, dict[str, str]] = {}


def _persist(key: str, value: str) -> None:
    from keprix.api.provider_settings import persist_env_value

    persist_env_value(key, value)


def resolve_id(integration_id: str | None) -> str | None:
    if not integration_id:
        return None
    req = get_integration(integration_id) or find_integration(integration_id)
    return req.id if req else None


def list_integrations_payload() -> dict[str, Any]:
    from keprix.integrations.companies_house.config import is_configured as ch_configured
    from keprix.integrations.companies_house.config import is_enabled as ch_enabled
    from keprix.integrations.notion.token_store import NotionTokenStore

    notion = NotionTokenStore()
    rows = []
    for summary in list_integration_summaries():
        iid = str(summary["id"])
        configured = False
        detail: dict[str, Any] = {}
        if iid == "notion":
            configured = notion.is_enabled()
            detail["token_set"] = notion.is_configured()
        elif iid == "companies_house":
            configured = ch_enabled() and ch_configured()
            detail["api_key_set"] = ch_configured()
            detail["enabled"] = ch_enabled()
        elif iid == "trello":
            configured = bool(os.getenv("TRELLO_API_KEY") and os.getenv("TRELLO_TOKEN"))
        elif iid == "google_workspace":
            try:
                from keprix.integrations.google_workspace.bridge import GoogleWorkspaceBridge

                status = GoogleWorkspaceBridge().status()
                configured = bool(status.get("connected") or status.get("authenticated"))
                detail = {k: v for k, v in status.items() if "token" not in str(k).lower()}
            except Exception as exc:  # noqa: BLE001
                detail = {"error": str(exc)}
        elif iid == "webhooks":
            from keprix.public_api.webhooks import get_webhook_store

            hooks = get_webhook_store().list_webhooks()
            configured = len(hooks) > 0
            detail = {"count": len(hooks)}
        rows.append(
            {
                "id": iid,
                "name": summary["name"],
                "aliases": summary["aliases"],
                "flow": summary["flow"],
                "configured": configured,
                "status": "connected" if configured else "not_configured",
                "detail": detail,
            }
        )
    return {"integrations": rows, "catalog": list_integration_summaries()}


def requirements_payload(integration_id: str) -> dict[str, Any]:
    req = get_integration(integration_id) or find_integration(integration_id)
    if req is None:
        return {"ok": False, "error": f"Unknown integration: {integration_id}"}
    required = [f for f in req.fields if not f.optional]
    first = required[0] if required else (req.fields[0] if req.fields else None)
    payload: dict[str, Any] = {
        "ok": True,
        "id": req.id,
        "name": req.name,
        "description": req.description,
        "flow": req.flow,
        "required_fields": [
            {
                "key": f.key,
                "label": f.label,
                "description": f.description,
                "sensitive": f.sensitive,
                "optional": f.optional,
                "example": f.example,
            }
            for f in req.fields
        ],
        "hint": "Prefer action=collect. Never send the user only to Settings.",
    }
    if first:
        ask = (
            sensitive_field_warning(field_label=first.label)
            if first.sensitive
            else f"Please send your {first.label}."
        )
        payload["next_field"] = {
            "key": first.key,
            "label": first.label,
            "description": first.description,
            "sensitive": first.sensitive,
            "ask": ask,
        }
    if req.flow == "oauth":
        payload["oauth_note"] = (
            "Google Workspace needs a browser consent step. "
            "Call configure with action that returns auth_url, then collect oauth_code."
        )
    return payload


def _session_key(integration_id: str, session_id: str | None) -> str:
    return f"{session_id or 'default'}::{integration_id}"


def _next_field(req, collected: dict[str, str]) -> dict[str, Any] | None:
    for fld in req.fields:
        if fld.optional:
            continue
        if not collected.get(fld.key):
            ask = (
                sensitive_field_warning(field_label=fld.label)
                if fld.sensitive
                else f"Please send your {fld.label}."
            )
            return {
                "key": fld.key,
                "label": fld.label,
                "description": fld.description,
                "sensitive": fld.sensitive,
                "ask": ask,
            }
    return None


def configure_integration(integration_id: str, credentials: dict[str, str]) -> dict[str, Any]:
    req = get_integration(integration_id) or find_integration(integration_id)
    if req is None:
        return {"ok": False, "error": f"Unknown integration: {integration_id}"}
    creds = {str(k): str(v).strip() for k, v in (credentials or {}).items() if v is not None and str(v).strip()}

    if req.id == "notion":
        token = creds.get("integration_token") or creds.get("token") or ""
        if not token:
            return {"ok": False, "error": "Missing integration_token"}
        _persist("NOTION_INTEGRATION_TOKEN", token)
        _persist("KEPRIX_NOTION_ENABLED", "true")
        return {
            "ok": True,
            "id": "notion",
            "configured": True,
            "message": "Notion token saved and enabled. No Settings scavenger hunt required.",
        }

    if req.id == "companies_house":
        api_key = creds.get("api_key") or creds.get("token") or ""
        if not api_key:
            return {"ok": False, "error": "Missing api_key", "next_field": {"key": "api_key"}}
        _persist("COMPANIES_HOUSE_API_KEY", api_key)
        _persist("KEPRIX_COMPANIES_HOUSE_ENABLED", "1")
        return {
            "ok": True,
            "id": "companies_house",
            "configured": True,
            "message": "Companies House API key saved. Search UK companies from /companies-house or agent tools.",
        }

    if req.id == "trello":
        api_key = creds.get("api_key") or ""
        token = creds.get("token") or ""
        if not api_key:
            return {"ok": False, "error": "Missing api_key", "next_field": {"key": "api_key"}}
        if not token:
            return {"ok": False, "error": "Missing token", "next_field": {"key": "token"}}
        _persist("TRELLO_API_KEY", api_key)
        _persist("TRELLO_TOKEN", token)
        return {
            "ok": True,
            "id": "trello",
            "configured": True,
            "message": "Trello credentials saved.",
        }

    if req.id == "google_workspace":
        if creds.get("credentials_path"):
            _persist("GOOGLE_WORKSPACE_CREDENTIALS_PATH", creds["credentials_path"])
        _persist("KEPRIX_GWS_ENABLED", "true")
        try:
            from keprix.integrations.google_workspace.bridge import GoogleWorkspaceBridge

            bridge = GoogleWorkspaceBridge()
            if creds.get("oauth_code"):
                public = bridge.exchange_callback({"code": creds["oauth_code"]})
                return {
                    "ok": True,
                    "id": "google_workspace",
                    "configured": True,
                    "status": public,
                    "message": "Google Workspace connected.",
                }
            auth = bridge.auth_url()
            return {
                "ok": True,
                "id": "google_workspace",
                "configured": False,
                "auth_url": auth.get("auth_url"),
                "next_field": {
                    "key": "oauth_code",
                    "label": "OAuth code",
                    "sensitive": True,
                    "ask": (
                        "Open the auth_url in a browser, then send me the OAuth code. "
                        + sensitive_field_warning(field_label="OAuth code")
                    ),
                },
                "message": "Open the Google consent URL, then reply with the OAuth code.",
            }
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}

    if req.id == "webhooks":
        url = creds.get("url") or ""
        if not url:
            return {"ok": False, "error": "Missing url"}
        events_raw = creds.get("events") or "chat.completed"
        events = [e.strip() for e in events_raw.split(",") if e.strip()] or ["chat.completed"]
        workspace_id = creds.get("workspace_id") or "default"
        from keprix.public_api.schemas import WebhookCreateRequest
        from keprix.public_api.webhooks import get_webhook_store

        record, secret = get_webhook_store().create(
            WebhookCreateRequest(url=url, events=events, workspace_id=workspace_id)
        )
        return {
            "ok": True,
            "id": "webhooks",
            "configured": True,
            "webhook": {
                "id": record.id,
                "url": record.url,
                "events": record.events,
                "workspace_id": record.workspace_id,
            },
            "signing_secret_once": secret,
            "message": (
                "Webhook created. Store the signing_secret_once now; "
                "it will not be shown again. Never speak it aloud."
            ),
        }

    return {"ok": False, "error": f"Unsupported integration: {req.id}"}


def collect_and_maybe_save(
    integration_id: str,
    credentials: dict[str, str] | None = None,
    *,
    session_id: str | None = None,
) -> dict[str, Any]:
    req = get_integration(integration_id) or find_integration(integration_id)
    if req is None:
        return {"ok": False, "error": f"Unknown integration: {integration_id}"}

    key = _session_key(req.id, session_id)
    sess = _SESSIONS.setdefault(key, {})
    for k, v in (credentials or {}).items():
        if v is not None and str(v).strip():
            sess[str(k)] = str(v).strip()

    # Google: start OAuth when collecting without code
    if req.id == "google_workspace" and "oauth_code" not in sess:
        started = configure_integration(req.id, dict(sess))
        if started.get("auth_url") and not started.get("configured"):
            started["complete"] = False
            started["collected_field_keys"] = sorted(sess.keys())
            return started
        if started.get("ok") and started.get("configured"):
            _SESSIONS.pop(key, None)
            started["complete"] = True
            return started

    nxt = _next_field(req, sess)
    if nxt is not None:
        return {
            "ok": True,
            "complete": False,
            "id": req.id,
            "name": req.name,
            "next_field": nxt,
            "collected_field_keys": sorted(sess.keys()),
            "message": (
                ("Got it." if credentials else f"Let's configure {req.name}.")
                + f" Next: {nxt['label']}."
            ),
        }

    result = configure_integration(req.id, dict(sess))
    if result.get("ok") and (result.get("configured") or result.get("signing_secret_once")):
        _SESSIONS.pop(key, None)
        result["complete"] = True
    elif result.get("auth_url"):
        result["complete"] = False
    return result


def remove_integration(integration_id: str, *, webhook_id: str | None = None) -> dict[str, Any]:
    req = get_integration(integration_id) or find_integration(integration_id)
    if req is None:
        return {"ok": False, "error": f"Unknown integration: {integration_id}"}

    if req.id == "notion":
        from keprix.api.provider_settings import remove_env_value

        remove_env_value("NOTION_INTEGRATION_TOKEN")
        remove_env_value("KEPRIX_NOTION_ENABLED")
        return {"ok": True, "id": "notion", "removed": True}

    if req.id == "companies_house":
        from keprix.api.provider_settings import remove_env_value

        remove_env_value("COMPANIES_HOUSE_API_KEY")
        remove_env_value("KEPRIX_COMPANIES_HOUSE_ENABLED")
        return {"ok": True, "id": "companies_house", "removed": True}

    if req.id == "trello":
        from keprix.api.provider_settings import remove_env_value

        remove_env_value("TRELLO_API_KEY")
        remove_env_value("TRELLO_TOKEN")
        return {"ok": True, "id": "trello", "removed": True}

    if req.id == "google_workspace":
        try:
            from keprix.integrations.google_workspace.bridge import GoogleWorkspaceBridge

            GoogleWorkspaceBridge().logout()
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}
        return {"ok": True, "id": "google_workspace", "removed": True}

    if req.id == "webhooks":
        if not webhook_id:
            return {"ok": False, "error": "webhook_id is required to remove a webhook"}
        from keprix.public_api.webhooks import get_webhook_store

        ok = get_webhook_store().delete(webhook_id)
        return {"ok": ok, "id": "webhooks", "removed": ok, "webhook_id": webhook_id}

    return {"ok": False, "error": f"Unsupported integration: {req.id}"}


def test_integration(integration_id: str) -> dict[str, Any]:
    listed = list_integrations_payload()
    for row in listed["integrations"]:
        if row["id"] == resolve_id(integration_id):
            return {
                "success": bool(row.get("configured")),
                "message": (
                    f"{row['name']} is connected"
                    if row.get("configured")
                    else f"{row['name']} is not configured"
                ),
                "detail": row.get("detail") or {},
            }
    return {"success": False, "message": f"Unknown integration: {integration_id}"}
