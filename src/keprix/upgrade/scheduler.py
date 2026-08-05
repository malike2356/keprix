"""Scheduled auto-upgrade policy helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .alerts import UpgradeAlertPreferences, UpgradeAlertStore
from .notifier import UpdateInfo, UpdateNotifier
from .versions import version_gt


@dataclass
class SchedulerDecision:
    should_run: bool
    reason: str


class UpgradeScheduler:
    """Evaluates whether an update should auto-apply during a maintenance window."""

    def __init__(self, product_path: Path):
        self.product_path = product_path.expanduser().resolve()
        self.store = UpgradeAlertStore(self.product_path)
        self.notifier = UpdateNotifier(self.product_path)

    def load_preferences(self) -> UpgradeAlertPreferences:
        return self.store.load_preferences()

    def save_preferences(self, preferences: UpgradeAlertPreferences) -> UpgradeAlertPreferences:
        return self.store.save_preferences(preferences)

    def evaluate(self, update: UpdateInfo, now: datetime | None = None) -> SchedulerDecision:
        prefs = self.store.load_preferences()
        current = now or datetime.now(timezone.utc)
        if prefs.auto_upgrade_policy == "manual":
            return SchedulerDecision(False, "manual policy")
        if not self._in_maintenance_window(prefs, current):
            return SchedulerDecision(False, "outside maintenance window")
        if prefs.auto_upgrade_policy == "security_only":
            if update.severity != "critical":
                return SchedulerDecision(False, "not a critical security update")
        if prefs.auto_upgrade_policy == "all_updates":
            if not update.compatible or update.risk_level == "high":
                return SchedulerDecision(False, "incompatible or high risk")
        if not version_gt(update.new_version, update.current_version):
            return SchedulerDecision(False, "already on target")
        return SchedulerDecision(True, "policy allows auto-upgrade")

    def maybe_run(self, now: datetime | None = None) -> dict[str, Any]:
        status = self.notifier.check_now()
        if not status.get("update_available"):
            return {"ran": False, "reason": "no update available", "status": status}
        update_data = status["update"]
        update = UpdateInfo(
            current_version=str(update_data["current_version"]),
            new_version=str(update_data["new_version"]),
            severity=str(update_data["severity"]),
            title=str(update_data["title"]),
            summary=str(update_data["summary"]),
            breaking_changes=list(update_data.get("breaking_changes") or []),
            new_features=list(update_data.get("new_features") or []),
            security_fixes=list(update_data.get("security_fixes") or []),
            deprecated=list(update_data.get("deprecated") or []),
            config_migrations=list(update_data.get("config_migrations") or []),
            release_url=str(update_data.get("release_url", "")),
            estimated_upgrade_time_seconds=int(update_data.get("estimated_upgrade_time_seconds", 30)),
            risk_level=str(update_data.get("risk_level", "none")),
            compatible=bool(update_data.get("compatible", True)),
        )
        decision = self.evaluate(update, now=now)
        if not decision.should_run:
            return {"ran": False, "reason": decision.reason, "status": status}
        from .service import UpgradeService

        service = UpgradeService(self.product_path)
        prefs = self.store.load_preferences()
        if prefs.require_tests_pass:
            dry = service.dry_run(update.new_version, skip_tests=False)
            if not dry.get("passed", False):
                return {"ran": False, "reason": "dry-run failed", "dry_run": dry}
        result = service.execute(update.new_version, force=True)
        return {"ran": True, "result": result, "status": status}

    def _in_maintenance_window(self, prefs: UpgradeAlertPreferences, now: datetime) -> bool:
        return now.weekday() == prefs.maintenance_day and now.hour == prefs.maintenance_hour
