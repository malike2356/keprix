"""Update notifier: poll changelog, classify severity, dispatch alerts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .alerts import UpgradeAlert, UpgradeAlertPreferences, UpgradeAlertStore, severity_meets_minimum
from .changelog import entries_between, load_changelog
from .check import check_upgrade
from .context import UpgradeContext, installed_keprix_version
from .dispatch import dispatch_discord, dispatch_slack, dispatch_webhook, render_email_text
from .events import emit_update_event
from .installability import check_target_installable
from .versions import version_gt


_SEVERITY_FROM_RISK = {
    "high": "high",
    "medium": "medium",
    "low": "low",
    "none": "medium",
    "blocked": "high",
}


@dataclass
class UpdateInfo:
    current_version: str
    new_version: str
    severity: str
    title: str
    summary: str
    breaking_changes: list[str]
    new_features: list[str]
    security_fixes: list[str]
    deprecated: list[str]
    config_migrations: list[str]
    release_url: str
    estimated_upgrade_time_seconds: int
    risk_level: str
    compatible: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "current_version": self.current_version,
            "new_version": self.new_version,
            "severity": self.severity,
            "title": self.title,
            "summary": self.summary,
            "breaking_changes": self.breaking_changes,
            "new_features": self.new_features,
            "security_fixes": self.security_fixes,
            "deprecated": self.deprecated,
            "config_migrations": self.config_migrations,
            "release_url": self.release_url,
            "estimated_upgrade_time_seconds": self.estimated_upgrade_time_seconds,
            "risk_level": self.risk_level,
            "compatible": self.compatible,
        }


class UpdateNotifier:
    """Checks for Keprix updates and records/dispatches alerts."""

    def __init__(self, product_path: Path):
        self.product_path = product_path.expanduser().resolve()
        self.store = UpgradeAlertStore(self.product_path)

    def check_now(self) -> dict[str, Any]:
        ctx = UpgradeContext.resolve(self.product_path, allow_default=True)
        target = ctx.resolve_target("latest")
        if not version_gt(target, ctx.installed_version):
            self.store._save_raw({**self.store._load_raw(), "last_check_at": _now_iso()})
            return {
                "update_available": False,
                "current_version": ctx.installed_version,
                "target_version": ctx.installed_version,
                "alerts": [],
            }

        installability = check_target_installable(target, cwd=self.product_path)
        if not installability.available:
            self.store._save_raw({**self.store._load_raw(), "last_check_at": _now_iso()})
            return {
                "update_available": False,
                "current_version": ctx.installed_version,
                "target_version": target,
                "installable": False,
                "recommendation": installability.recommendation,
                "alerts": [item.to_dict() for item in self.store.list_alerts()],
            }

        update = self._build_update_info(ctx, target)
        alert = self._record_alert(update)
        prefs = self.store.load_preferences()
        if not alert.dismissed:
            self._dispatch_external(alert, prefs, ctx.manifest.product_slug)
            if prefs.in_app_enabled and severity_meets_minimum(alert.severity, prefs.in_app_min_severity):
                emit_update_event(
                    "update_available",
                    {"alert": alert.to_dict(), "product": ctx.manifest.product_name},
                )
        return {
            "update_available": not alert.dismissed,
            "current_version": ctx.installed_version,
            "target_version": target,
            "installable": True,
            "update": update.to_dict(),
            "alert": alert.to_dict(),
            "alerts": [item.to_dict() for item in self.store.list_alerts()],
        }

    def _build_update_info(self, ctx: UpgradeContext, target: str) -> UpdateInfo:
        releases = load_changelog(ctx.changelog_path)
        changelog = entries_between(ctx.installed_version, target, releases)
        check = check_upgrade(
            ctx.manifest.to_upgrade_info(),
            ctx.installed_version,
            target,
            ctx.available_versions,
            changelog=changelog,
            changelog_url=f"https://github.com/malike2356/keprix/releases/tag/v{target}",
        )
        breaking = [e.get("title", e.get("id", "breaking")) for e in check.breaking_changes]
        features = [e.get("title", e.get("id", "feature")) for e in check.new_features]
        deprecated = [e.get("title", e.get("id", "deprecation")) for e in check.deprecated_features]
        migrations = [
            e.get("title", e.get("id", "migration")) for e in check.config_migrations_required
        ]
        security = [
            e.get("title", "")
            for e in changelog
            if e.get("type") in {"security", "fix"} and "security" in str(e.get("title", "")).lower()
        ]
        severity = _classify_severity(check.risk, security, breaking)
        summary = check.recommendation
        return UpdateInfo(
            current_version=ctx.installed_version,
            new_version=target,
            severity=severity,
            title=f"Keprix {target} available",
            summary=summary,
            breaking_changes=breaking,
            new_features=features,
            security_fixes=security,
            deprecated=deprecated,
            config_migrations=migrations,
            release_url=check.changelog_url,
            estimated_upgrade_time_seconds=30 + (len(migrations) * 10),
            risk_level=check.risk,
            compatible=check.compatible,
        )

    def _record_alert(self, update: UpdateInfo) -> UpgradeAlert:
        alert = UpgradeAlert(
            id="",
            target_version=update.new_version,
            severity=update.severity,
            title=update.title,
            summary=update.summary,
            risk_level=update.risk_level,
            compatible=update.compatible,
            breaking_count=len(update.breaking_changes),
            feature_count=len(update.new_features),
            release_url=update.release_url,
        )
        return self.store.upsert_alert(alert)

    def _dispatch_external(
        self,
        alert: UpgradeAlert,
        prefs: UpgradeAlertPreferences,
        product_slug: str,
    ) -> None:
        if _in_quiet_hours(prefs):
            return
        dispatch_slack(alert, prefs, product_slug)
        dispatch_discord(alert, prefs, product_slug)
        dispatch_webhook(alert, prefs, product_slug)
        if prefs.email_enabled and severity_meets_minimum(alert.severity, prefs.email_min_severity):
            emit_update_event(
                "upgrade_email_requested",
                {
                    "subject": f"Keprix {alert.target_version} available",
                    "body": render_email_text(alert, product_slug),
                },
            )


def _classify_severity(risk: str, security_fixes: list[str], breaking: list[str]) -> str:
    if security_fixes:
        return "critical"
    if breaking or risk == "high":
        return "high"
    return _SEVERITY_FROM_RISK.get(risk, "info")


def _in_quiet_hours(prefs: UpgradeAlertPreferences) -> bool:
    if not prefs.quiet_hours_enabled:
        return False
    hour = datetime.now().hour
    start = prefs.quiet_hours_start
    end = prefs.quiet_hours_end
    if start <= end:
        return start <= hour <= end
    return hour >= start or hour <= end


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
