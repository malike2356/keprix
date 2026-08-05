"""Tests for upgrade/alerts.py."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from keprix.upgrade.alerts import UpgradeAlert, UpgradeAlertPreferences, UpgradeAlertStore, severity_meets_minimum


def _write_product(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "keprix.yaml").write_text(
        """
product:
  name: AlertProduct
  slug: alertproduct
keprix:
  min_version: "0.2.0"
  tested_against: "0.3.0"
features: {}
""".strip()
        + "\n",
        encoding="utf-8",
    )


def test_severity_meets_minimum_ordering():
    assert severity_meets_minimum("high", "medium")
    assert not severity_meets_minimum("low", "medium")


def test_alert_store_upsert_and_list(tmp_path: Path):
    _write_product(tmp_path)
    store = UpgradeAlertStore(tmp_path)
    alert = UpgradeAlert(
        id="",
        target_version="0.7.0",
        severity="medium",
        title="Keprix 0.7.0 available",
        summary="Safe to upgrade",
        risk_level="low",
        compatible=True,
    )
    saved = store.upsert_alert(alert)
    assert saved.id
    listed = store.list_alerts()
    assert len(listed) == 1
    assert listed[0].target_version == "0.7.0"


def test_alert_store_dismiss_and_snooze(tmp_path: Path):
    _write_product(tmp_path)
    store = UpgradeAlertStore(tmp_path)
    alert = store.upsert_alert(
        UpgradeAlert(
            id="",
            target_version="0.7.0",
            severity="medium",
            title="Update",
            summary="Summary",
            risk_level="low",
            compatible=True,
        )
    )
    assert store.dismiss_alert(alert.id)
    assert store.list_alerts() == []
    assert store.get_alert(alert.id) is not None

    future = (datetime.now(timezone.utc) + timedelta(hours=2)).replace(microsecond=0).isoformat()
    raw = store._load_raw()
    raw["alerts"][0]["dismissed"] = False
    raw["alerts"][0]["snoozed_until"] = future
    store._save_raw(raw)
    assert store.list_alerts() == []

    assert store.snooze_alert(alert.id, hours=1)
    assert store.list_alerts() == []


def test_preferences_round_trip(tmp_path: Path):
    _write_product(tmp_path)
    store = UpgradeAlertStore(tmp_path)
    prefs = UpgradeAlertPreferences(
        in_app_enabled=False,
        slack_enabled=True,
        slack_webhook_url="https://hooks.example/slack",
        auto_upgrade_policy="security_only",
    )
    store.save_preferences(prefs)
    loaded = store.load_preferences()
    assert loaded.in_app_enabled is False
    assert loaded.slack_enabled is True
    assert loaded.auto_upgrade_policy == "security_only"


def test_status_includes_alert_count(tmp_path: Path):
    _write_product(tmp_path)
    store = UpgradeAlertStore(tmp_path)
    store.upsert_alert(
        UpgradeAlert(
            id="",
            target_version="0.6.0",
            severity="low",
            title="Update",
            summary="Summary",
            risk_level="low",
            compatible=True,
        )
    )
    status = store.status()
    assert status["alert_count"] == 1
    assert status["preferences"]["in_app_enabled"] is True
