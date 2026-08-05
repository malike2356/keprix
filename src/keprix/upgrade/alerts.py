"""Persisted in-app upgrade alerts, preferences, and scheduler policy."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass
class UpgradeAlert:
    id: str
    target_version: str
    severity: str
    title: str
    summary: str
    risk_level: str
    compatible: bool
    breaking_count: int = 0
    feature_count: int = 0
    release_url: str = ""
    dismissed: bool = False
    snoozed_until: str | None = None
    created_at: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "target_version": self.target_version,
            "severity": self.severity,
            "title": self.title,
            "summary": self.summary,
            "risk_level": self.risk_level,
            "compatible": self.compatible,
            "breaking_count": self.breaking_count,
            "feature_count": self.feature_count,
            "release_url": self.release_url,
            "dismissed": self.dismissed,
            "snoozed_until": self.snoozed_until,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "UpgradeAlert":
        return cls(
            id=str(data.get("id", "")),
            target_version=str(data.get("target_version", "")),
            severity=str(data.get("severity", "info")),
            title=str(data.get("title", "")),
            summary=str(data.get("summary", "")),
            risk_level=str(data.get("risk_level", "none")),
            compatible=bool(data.get("compatible", True)),
            breaking_count=int(data.get("breaking_count", 0)),
            feature_count=int(data.get("feature_count", 0)),
            release_url=str(data.get("release_url", "")),
            dismissed=bool(data.get("dismissed", False)),
            snoozed_until=data.get("snoozed_until"),
            created_at=str(data.get("created_at", _now_iso())),
        )


@dataclass
class UpgradeAlertPreferences:
    in_app_enabled: bool = True
    in_app_min_severity: str = "medium"
    email_enabled: bool = False
    email_min_severity: str = "low"
    slack_enabled: bool = False
    slack_webhook_url: str = ""
    discord_enabled: bool = False
    discord_webhook_url: str = ""
    webhook_enabled: bool = False
    webhook_url: str = ""
    quiet_hours_enabled: bool = False
    quiet_hours_start: int = 22
    quiet_hours_end: int = 7
    auto_upgrade_policy: str = "manual"  # manual | security_only | all_updates
    maintenance_day: int = 6  # Sunday
    maintenance_hour: int = 3
    require_tests_pass: bool = True
    notify_after_upgrade: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "in_app_enabled": self.in_app_enabled,
            "in_app_min_severity": self.in_app_min_severity,
            "email_enabled": self.email_enabled,
            "email_min_severity": self.email_min_severity,
            "slack_enabled": self.slack_enabled,
            "slack_webhook_url": self.slack_webhook_url,
            "discord_enabled": self.discord_enabled,
            "discord_webhook_url": self.discord_webhook_url,
            "webhook_enabled": self.webhook_enabled,
            "webhook_url": self.webhook_url,
            "quiet_hours_enabled": self.quiet_hours_enabled,
            "quiet_hours_start": self.quiet_hours_start,
            "quiet_hours_end": self.quiet_hours_end,
            "auto_upgrade_policy": self.auto_upgrade_policy,
            "maintenance_day": self.maintenance_day,
            "maintenance_hour": self.maintenance_hour,
            "require_tests_pass": self.require_tests_pass,
            "notify_after_upgrade": self.notify_after_upgrade,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "UpgradeAlertPreferences":
        return cls(
            in_app_enabled=bool(data.get("in_app_enabled", True)),
            in_app_min_severity=str(data.get("in_app_min_severity", "medium")),
            email_enabled=bool(data.get("email_enabled", False)),
            email_min_severity=str(data.get("email_min_severity", "low")),
            slack_enabled=bool(data.get("slack_enabled", False)),
            slack_webhook_url=str(data.get("slack_webhook_url", "")),
            discord_enabled=bool(data.get("discord_enabled", False)),
            discord_webhook_url=str(data.get("discord_webhook_url", "")),
            webhook_enabled=bool(data.get("webhook_enabled", False)),
            webhook_url=str(data.get("webhook_url", "")),
            quiet_hours_enabled=bool(data.get("quiet_hours_enabled", False)),
            quiet_hours_start=int(data.get("quiet_hours_start", 22)),
            quiet_hours_end=int(data.get("quiet_hours_end", 7)),
            auto_upgrade_policy=str(data.get("auto_upgrade_policy", "manual")),
            maintenance_day=int(data.get("maintenance_day", 6)),
            maintenance_hour=int(data.get("maintenance_hour", 3)),
            require_tests_pass=bool(data.get("require_tests_pass", True)),
            notify_after_upgrade=bool(data.get("notify_after_upgrade", True)),
        )


_SEVERITY_RANK = {
    "info": 0,
    "low": 1,
    "medium": 2,
    "high": 3,
    "critical": 4,
}


def severity_meets_minimum(severity: str, minimum: str) -> bool:
    return _SEVERITY_RANK.get(severity, 0) >= _SEVERITY_RANK.get(minimum, 0)


class UpgradeAlertStore:
    """JSON file store for upgrade alerts and notification preferences."""

    def __init__(self, product_path: Path):
        self.product_path = product_path.expanduser().resolve()
        self.state_path = self.product_path / ".keprix" / "upgrade" / "alerts_state.json"

    def _load_raw(self) -> dict[str, Any]:
        if not self.state_path.exists():
            return {"alerts": [], "preferences": UpgradeAlertPreferences().to_dict()}
        try:
            data = json.loads(self.state_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {"alerts": [], "preferences": UpgradeAlertPreferences().to_dict()}
        if not isinstance(data, dict):
            return {"alerts": [], "preferences": UpgradeAlertPreferences().to_dict()}
        return data

    def _save_raw(self, data: dict[str, Any]) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def list_alerts(self, *, include_dismissed: bool = False) -> list[UpgradeAlert]:
        raw = self._load_raw()
        alerts = [UpgradeAlert.from_dict(item) for item in raw.get("alerts", []) if isinstance(item, dict)]
        now = datetime.now(timezone.utc)
        visible: list[UpgradeAlert] = []
        for alert in alerts:
            if alert.dismissed and not include_dismissed:
                continue
            if alert.snoozed_until:
                try:
                    until = datetime.fromisoformat(alert.snoozed_until)
                    if until.tzinfo is None:
                        until = until.replace(tzinfo=timezone.utc)
                    if until > now:
                        continue
                except ValueError:
                    pass
            visible.append(alert)
        return visible

    def upsert_alert(self, alert: UpgradeAlert) -> UpgradeAlert:
        raw = self._load_raw()
        alerts = [UpgradeAlert.from_dict(item) for item in raw.get("alerts", []) if isinstance(item, dict)]
        replaced = False
        for index, existing in enumerate(alerts):
            if existing.target_version == alert.target_version:
                alert.id = existing.id or alert.id
                # Preserve operator dismiss/snooze so a re-check does not revive the banner.
                alert.dismissed = existing.dismissed
                alert.snoozed_until = existing.snoozed_until
                alerts[index] = alert
                replaced = True
                break
        if not replaced:
            if not alert.id:
                alert.id = str(uuid.uuid4())
            alerts.append(alert)
        raw["alerts"] = [item.to_dict() for item in alerts]
        raw["last_check_at"] = _now_iso()
        self._save_raw(raw)
        return alert

    def get_alert(self, alert_id: str) -> UpgradeAlert | None:
        for alert in self.list_alerts(include_dismissed=True):
            if alert.id == alert_id:
                return alert
        return None

    def dismiss_alert(self, alert_id: str) -> bool:
        raw = self._load_raw()
        changed = False
        alerts: list[dict[str, Any]] = []
        for item in raw.get("alerts", []):
            if not isinstance(item, dict):
                continue
            if item.get("id") == alert_id:
                item["dismissed"] = True
                changed = True
            alerts.append(item)
        if changed:
            raw["alerts"] = alerts
            self._save_raw(raw)
        return changed

    def snooze_alert(self, alert_id: str, hours: int = 24) -> bool:
        raw = self._load_raw()
        changed = False
        until = datetime.now(timezone.utc).timestamp() + (hours * 3600)
        snooze_iso = datetime.fromtimestamp(until, tz=timezone.utc).replace(microsecond=0).isoformat()
        alerts: list[dict[str, Any]] = []
        for item in raw.get("alerts", []):
            if not isinstance(item, dict):
                continue
            if item.get("id") == alert_id:
                item["snoozed_until"] = snooze_iso
                item["dismissed"] = False
                changed = True
            alerts.append(item)
        if changed:
            raw["alerts"] = alerts
            self._save_raw(raw)
        return changed

    def load_preferences(self) -> UpgradeAlertPreferences:
        raw = self._load_raw()
        prefs = raw.get("preferences") or {}
        if not isinstance(prefs, dict):
            prefs = {}
        return UpgradeAlertPreferences.from_dict(prefs)

    def save_preferences(self, preferences: UpgradeAlertPreferences) -> UpgradeAlertPreferences:
        raw = self._load_raw()
        raw["preferences"] = preferences.to_dict()
        self._save_raw(raw)
        return preferences

    def status(self) -> dict[str, Any]:
        alerts = self.list_alerts()
        raw = self._load_raw()
        return {
            "alert_count": len(alerts),
            "last_check_at": raw.get("last_check_at"),
            "alerts": [alert.to_dict() for alert in alerts],
            "preferences": self.load_preferences().to_dict(),
        }
