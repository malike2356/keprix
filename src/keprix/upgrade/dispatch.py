"""Dispatch upgrade alerts to external channels."""

from __future__ import annotations

import json
from typing import Any

import httpx

from .alerts import UpgradeAlert, UpgradeAlertPreferences, severity_meets_minimum


def _post_json(url: str, payload: dict[str, Any], timeout: float = 5.0) -> bool:
    if not url:
        return False
    try:
        response = httpx.post(url, json=payload, timeout=timeout)
        return response.status_code < 400
    except httpx.HTTPError:
        return False


def dispatch_slack(alert: UpgradeAlert, prefs: UpgradeAlertPreferences, product: str) -> bool:
    if not prefs.slack_enabled or not severity_meets_minimum(alert.severity, "high"):
        return False
    payload = {
        "text": f"Keprix {alert.target_version} available for {product}",
        "attachments": [
            {
                "color": "#439FE0",
                "title": alert.title,
                "text": alert.summary,
                "fields": [
                    {"title": "Risk", "value": alert.risk_level.upper(), "short": True},
                    {"title": "Severity", "value": alert.severity.upper(), "short": True},
                ],
            }
        ],
    }
    return _post_json(prefs.slack_webhook_url, payload)


def dispatch_discord(alert: UpgradeAlert, prefs: UpgradeAlertPreferences, product: str) -> bool:
    if not prefs.discord_enabled or not severity_meets_minimum(alert.severity, "medium"):
        return False
    embed = {
        "title": f"Keprix {alert.target_version} for {product}",
        "description": alert.summary,
        "fields": [
            {"name": "Risk", "value": alert.risk_level.upper(), "inline": True},
            {"name": "Severity", "value": alert.severity.upper(), "inline": True},
        ],
    }
    if alert.release_url:
        embed["url"] = alert.release_url
    return _post_json(prefs.discord_webhook_url, {"embeds": [embed]})


def dispatch_webhook(alert: UpgradeAlert, prefs: UpgradeAlertPreferences, product: str) -> bool:
    if not prefs.webhook_enabled:
        return False
    payload = {
        "event": "keprix.update_available",
        "product": product,
        "target_version": alert.target_version,
        "severity": alert.severity,
        "risk": alert.risk_level,
        "compatible": alert.compatible,
        "title": alert.title,
        "summary": alert.summary,
        "release_url": alert.release_url,
    }
    return _post_json(prefs.webhook_url, payload)


def render_email_text(alert: UpgradeAlert, product: str) -> str:
    lines = [
        f"Keprix {alert.target_version} is available for {product}.",
        "",
        alert.summary,
        "",
        f"Severity: {alert.severity.upper()}",
        f"Risk: {alert.risk_level.upper()}",
        f"Breaking changes: {alert.breaking_count}",
        f"New features: {alert.feature_count}",
    ]
    if alert.release_url:
        lines.extend(["", f"Release notes: {alert.release_url}"])
    lines.extend(["", "Manage notifications in Settings > Keprix upgrades."])
    return "\n".join(lines)
