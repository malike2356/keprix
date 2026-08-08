# Keprix - Prompt 274: Upgrade alerts, notifier, API, and GUI

**Status:** Shipped (`upgrade/alerts.py`, `notifier.py`, `events.py`, `dispatch.py`, `scheduler.py`, `service.py`, `/api/keprix/upgrade/*`, `UpgradeBanner`, `/settings/upgrade`, 77 tests at archive time).

---

# Prompt 86; Keprix Upgrade Alerts, Notices & GUI UX

## 1. The Problem

Prompt 85 gave us `keprix upgrade --check` / `--dry-run` / `--to X`. That works for developers. But:

- **End users** of AbbiS, Petraclus, or FleetZ aren't developers. They don't open terminals.
- **No one knows** an upgrade exists unless they manually run `--check`.
- **Security patches** need immediate attention; email, Slack, push notification.
- **New features** should be showcased, not buried in a changelog file.
- **Upgrade anxiety** is real; users fear clicking "Upgrade" without knowing what'll happen.

This prompt builds the notification layer and GUI that makes upgrading Keprix (and any product built on it) trivial for everyone.

---

## 2. Architecture Overview

```
┌─────────────────────────────────────────────┐
│              KEPRIX UPDATE SERVICE           │
│         (GitHub Releases / PyPI / API)       │
└──────────────────┬──────────────────────────┘
                   │ Poll (every 6h, or webhook)
                   ▼
┌─────────────────────────────────────────────┐
│          UPDATE NOTIFIER ENGINE              │
│  ┌──────────┐ ┌──────────┐ ┌──────────────┐ │
│  │ Version  │ │ Severity │ │ Compatibility│ │
│  │ Monitor  │ │Classifier│ │   Pre-Check  │ │
│  └────┬─────┘ └────┬─────┘ └──────┬───────┘ │
│       └─────────────┼──────────────┘         │
│                     ▼                        │
│            ┌────────────────┐                │
│            │ ALERT DISPATCH │                │
│            └───────┬────────┘                │
└────────────────────┼─────────────────────────┘
                     │
        ┌────────────┼────────────┐
        ▼            ▼            ▼
   ┌─────────┐ ┌─────────┐ ┌──────────────┐
   │ IN-APP  │ │  EMAIL  │ │ SLACK/DISCORD│
   │ Banner  │ │ Digest  │ │  Webhook     │
   └────┬────┘ └────┬────┘ └──────┬───────┘
        │           │             │
        ▼           ▼             ▼
   ┌─────────────────────────────────────────┐
   │           "UPGRADE AVAILABLE"            │
   │  Keprix 0.7.0; 7 new features, 0 breaks│
   │  [Review Changes]  [Upgrade Now]  [Later]│
   └─────────────────────────────────────────┘
                    │
                    ▼  (User clicks "Upgrade Now")
   ┌─────────────────────────────────────────┐
   │          UPGRADE WIZARD (GUI)            │
   │  Step 1: Compatibility Check ─ Done:        │
   │  Step 2: Run Tests          ─ Done:  247/247│
   │  Step 3: Backup             ─ Done:  2.3 MB │
   │  Step 4: Install            ─ ⏳ 67%    │
   │  Step 5: Migrate Config     ─ ⏸         │
   │  Step 6: Verify             ─ ⏸         │
   │                                          │
   │  [Pause]  [Cancel]  [Rollback]           │
   └─────────────────────────────────────────┘
```

---

## 3. Update Notifier Engine

### 3.1 Version Monitor

Runs as a background thread in every Keprix-based product. Polls for updates.

```python
# keprix/upgrade/notifier.py

import json
import time
import threading
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import List, Optional, Callable

import httpx
from packaging.version import Version

from keprix.config import KeprixConfig
from keprix.extensions.manifest import ExtensionManifest


class Severity(Enum):
    CRITICAL = "critical"     # Security patch, data loss fix; URGENT
    HIGH = "high"             # Breaking change fix, critical bug
    MEDIUM = "medium"         # New feature, performance improvement
    LOW = "low"               # Minor fixes, docs, deprecation warnings
    INFO = "info"             # Announcements, blog posts


class AlertChannel(Enum):
    IN_APP = "in_app"         # Banner/toast in the product UI
    EMAIL = "email"           # Email digest (daily/weekly)
    SLACK = "slack"           # Slack webhook
    DISCORD = "discord"       # Discord webhook
    WEBHOOK = "webhook"       # Generic webhook (custom integrations)
    PUSH = "push"             # Mobile/desktop push notification
    SMS = "sms"               # Text message (critical only)


@dataclass
class UpdateInfo:
    """Describes an available Keprix update."""
    current_version: Version
    new_version: Version
    severity: Severity
    title: str
    summary: str
    breaking_changes: List[str]
    new_features: List[str]
    security_fixes: List[str]
    deprecated: List[str]
    config_migrations: List[str]
    release_date: datetime
    release_url: str
    estimated_upgrade_time_seconds: int
    risk_level: str            # "none", "low", "medium", "high"
    compatible: bool
    requires_downtime: bool
    requires_reboot: bool


@dataclass
class AlertPreference:
    """Per-user, per-channel notification settings."""
    user_id: str
    channel: AlertChannel
    min_severity: Severity     # Don't send alerts below this level
    quiet_hours_start: Optional[int] = None   # Hour (0-23)
    quiet_hours_end: Optional[int] = None     # Hour (0-23)
    digest_frequency: str = "instant"  # "instant", "daily", "weekly"
    enabled: bool = True


class UpdateNotifier:
    """
    Background service that monitors for Keprix updates and dispatches alerts.

    Polls the Keprix update endpoint (GitHub releases, PyPI, or custom server).
    Classifies severity. Checks compatibility against the product manifest.
    Dispatches to configured channels based on user preferences.
    """

    UPDATE_CHECK_INTERVAL = 6 * 3600   # 6 hours default
    UPDATE_ENDPOINT = "https://api.keprix.dev/v1/releases"  # Example

    def __init__(
        self,
        manifest: ExtensionManifest,
        config: KeprixConfig,
        product_path: Path,
    ):
        self.manifest = manifest
        self.config = config
        self.product_path = product_path
        self.state_file = product_path / ".keprix" / "upgrade" / "notifier_state.json"
        self._alerts_sent: dict = self._load_state()
        self._subscribers: dict[str, List[AlertPreference]] = {}
        self._running = False
        self._thread: Optional[threading.Thread] = None

    # ── Lifecycle ──────────────────────────────────────────

    def start(self):
        """Start background polling."""
        self._running = True
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()

    def stop(self):
        """Stop background polling."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)

    def _poll_loop(self):
        """Background thread: poll → classify → dispatch → sleep."""
        while self._running:
            try:
                updates = self._fetch_updates()
                for update in updates:
                    if not self._already_alerted(update):
                        self._classify_and_dispatch(update)
            except Exception as e:
                # Log but don't crash; notification failure shouldn't
                # take down the product
                print(f"[UpdateNotifier] Poll error: {e}")

            time.sleep(self.UPDATE_CHECK_INTERVAL)

    # ── Fetch ──────────────────────────────────────────────

    def _fetch_updates(self) -> List[UpdateInfo]:
        """Fetch available Keprix versions newer than current."""
        current = self.config.installed_keprix_version

        try:
            response = httpx.get(
                self.UPDATE_ENDPOINT,
                params={
                    "product": self.manifest.product.slug,
                    "current_version": str(current),
                    "min_version": self.manifest.keprix.min_version,
                },
                timeout=10,
            )
            response.raise_for_status()

            releases = response.json().get("releases", [])
        except httpx.HTTPError:
            # Fallback: use GitHub releases API
            releases = self._fetch_from_github()

        updates = []
        for rel in releases:
            version = Version(rel["version"])
            if version <= current:
                continue

            # Pre-check compatibility
            compatible = True
            if self.manifest.keprix.incompatible_with:
                compatible = str(version) not in self.manifest.keprix.incompatible_with

            # Classify severity
            severity = self._classify_severity(rel)

            updates.append(UpdateInfo(
                current_version=current,
                new_version=version,
                severity=severity,
                title=rel.get("title", f"Keprix {version}"),
                summary=rel.get("summary", ""),
                breaking_changes=rel.get("breaking_changes", []),
                new_features=rel.get("new_features", []),
                security_fixes=rel.get("security_fixes", []),
                deprecated=rel.get("deprecated", []),
                config_migrations=rel.get("config_migrations", []),
                release_date=datetime.fromisoformat(rel["release_date"]),
                release_url=rel.get("release_url", f"https://github.com/malike2356/keprix/releases/tag/v{version}"),
                estimated_upgrade_time_seconds=rel.get("estimated_time", 30),
                risk_level=self._compute_risk(rel),
                compatible=compatible,
                requires_downtime=rel.get("requires_downtime", False),
                requires_reboot=rel.get("requires_reboot", False),
            ))

        return updates

    def _fetch_from_github(self) -> list:
        """Fallback: fetch releases from GitHub API."""
        response = httpx.get(
            "https://api.github.com/repos/malike2356/keprix/releases",
            headers={"Accept": "application/vnd.github+json"},
            timeout=10,
        )
        if response.status_code != 200:
            return []

        releases = []
        for rel in response.json():
            # Parse the body for structured changelog
            releases.append({
                "version": rel["tag_name"].lstrip("v"),
                "title": rel["name"],
                "summary": rel["body"][:500] if rel.get("body") else "",
                "release_date": rel["published_at"],
                "release_url": rel["html_url"],
                "breaking_changes": [],
                "new_features": [],
                "security_fixes": [],
                "deprecated": [],
                "config_migrations": [],
                "estimated_time": 30,
                "requires_downtime": False,
                "requires_reboot": False,
            })

        return releases

    # ── Classify ───────────────────────────────────────────

    def _classify_severity(self, release: dict) -> Severity:
        """Determine how urgent this update is."""
        if release.get("security_fixes"):
            # Any security fix → at least HIGH
            if any("critical" in fix.lower() or "cve" in fix.lower()
                   for fix in release["security_fixes"]):
                return Severity.CRITICAL
            return Severity.HIGH

        if release.get("breaking_changes"):
            return Severity.HIGH

        if release.get("new_features"):
            return Severity.MEDIUM

        if release.get("deprecated"):
            return Severity.LOW

        return Severity.INFO

    def _compute_risk(self, release: dict) -> str:
        """Compute upgrade risk for display."""
        if release.get("breaking_changes"):
            return "high"
        if release.get("deprecated"):
            return "medium"
        if release.get("config_migrations"):
            return "low"
        return "none"

    # ── Dispatch ───────────────────────────────────────────

    def _classify_and_dispatch(self, update: UpdateInfo):
        """Route update to all subscribed channels at or above min severity."""
        for user_id, preferences in self._subscribers.items():
            for pref in preferences:
                if not pref.enabled:
                    continue

                # Severity gate
                if update.severity.value < pref.min_severity.value:
                    continue

                # Quiet hours gate
                if self._in_quiet_hours(pref):
                    continue

                # Dispatch per channel
                channel_handlers = {
                    AlertChannel.IN_APP: self._send_in_app,
                    AlertChannel.EMAIL: self._send_email,
                    AlertChannel.SLACK: self._send_slack,
                    AlertChannel.DISCORD: self._send_discord,
                    AlertChannel.WEBHOOK: self._send_webhook,
                    AlertChannel.PUSH: self._send_push,
                    AlertChannel.SMS: self._send_sms,
                }

                handler = channel_handlers.get(pref.channel)
                if handler:
                    handler(update, user_id, pref)

        # Record that we alerted for this version
        self._alerts_sent[str(update.new_version)] = datetime.now().isoformat()
        self._save_state()

    # ── Channel Handlers ───────────────────────────────────

    def _send_in_app(self, update: UpdateInfo, user_id: str, pref: AlertPreference):
        """Emit an in-app notification event (banner, toast, bell icon)."""
        # This publishes to the product's internal event bus.
        # The GUI layer listens and renders the banner.
        from keprix.upgrade.events import emit_update_event

        emit_update_event("update_available", {
            "update": update,
            "user_id": user_id,
            "actions": ["review", "upgrade", "dismiss", "snooze"],
        })

    def _send_email(self, update: UpdateInfo, user_id: str, pref: AlertPreference):
        """Send email notification via configured mail provider."""
        # In production, use Resend, SendGrid, SES, or SMTP
        from keprix.notifications.email import send_email

        subject_map = {
            Severity.CRITICAL: f" CRITICAL: Keprix {update.new_version}; Security Update",
            Severity.HIGH: f"WARNING:  Important: Keprix {update.new_version} Available",
            Severity.MEDIUM: f" Keprix {update.new_version}; New Features",
            Severity.LOW: f" Keprix {update.new_version}; Minor Update",
            Severity.INFO: f"ℹ Keprix {update.new_version}; Release Notes",
        }

        send_email(
            to=self._get_user_email(user_id),
            subject=subject_map.get(update.severity, f"Keprix {update.new_version}"),
            html=self._render_email_template(update),
        )

    def _send_slack(self, update: UpdateInfo, user_id: str, pref: AlertPreference):
        """Post to Slack via webhook."""
        webhook_url = self._get_slack_webhook(user_id)
        if not webhook_url:
            return

        color_map = {
            Severity.CRITICAL: "#FF0000",
            Severity.HIGH: "#FFA500", 
            Severity.MEDIUM: "#36A64F",
            Severity.LOW: "#439FE0",
            Severity.INFO: "#808080",
        }

        payload = {
            "attachments": [{
                "color": color_map.get(update.severity, "#808080"),
                "title": f"Keprix {update.new_version}; {update.severity.value.upper()}",
                "text": update.summary,
                "fields": [
                    {"title": "Current Version", "value": str(update.current_version), "short": True},
                    {"title": "New Version", "value": str(update.new_version), "short": True},
                    {"title": "Risk", "value": update.risk_level.upper(), "short": True},
                    {"title": "Est. Time", "value": f"~{update.estimated_upgrade_time_seconds}s", "short": True},
                ],
                "footer": f"{update.release_date.strftime('%B %d, %Y')} · <{update.release_url}|View Release>",
            }]
        }

        httpx.post(webhook_url, json=payload, timeout=5)

    def _send_discord(self, update: UpdateInfo, user_id: str, pref: AlertPreference):
        """Post to Discord via webhook."""
        webhook_url = self._get_discord_webhook(user_id)
        if not webhook_url:
            return

        emoji_map = {
            Severity.CRITICAL: "",
            Severity.HIGH: "",
            Severity.MEDIUM: "",
            Severity.LOW: "",
            Severity.INFO: "",
        }

        embed = {
            "title": f"{emoji_map.get(update.severity, '')} Keprix {update.new_version}",
            "description": update.summary,
            "color": {
                Severity.CRITICAL: 0xFF0000,
                Severity.HIGH: 0xFFA500,
                Severity.MEDIUM: 0x36A64F,
                Severity.LOW: 0x439FE0,
                Severity.INFO: 0x808080,
            }.get(update.severity, 0x808080),
            "fields": [
                {"name": "Current", "value": f"`{update.current_version}`", "inline": True},
                {"name": "New", "value": f"`{update.new_version}`", "inline": True},
                {"name": "Risk", "value": update.risk_level.upper(), "inline": True},
            ],
            "timestamp": update.release_date.isoformat(),
            "url": update.release_url,
        }

        httpx.post(webhook_url, json={"embeds": [embed]}, timeout=5)

    def _send_webhook(self, update: UpdateInfo, user_id: str, pref: AlertPreference):
        """POST to a custom webhook URL."""
        webhook_url = self._get_custom_webhook(user_id)
        if not webhook_url:
            return

        httpx.post(webhook_url, json={
            "event": "keprix.update_available",
            "product": self.manifest.product.slug,
            "current_version": str(update.current_version),
            "new_version": str(update.new_version),
            "severity": update.severity.value,
            "risk": update.risk_level,
            "release_url": update.release_url,
            "timestamp": datetime.now().isoformat(),
        }, timeout=5)

    def _send_push(self, update: UpdateInfo, user_id: str, pref: AlertPreference):
        """Send mobile/desktop push notification."""
        # Integrate with OneSignal, Firebase, or native OS notifications
        from keprix.notifications.push import send_push

        send_push(
            user_id=user_id,
            title=f"Keprix {update.new_version} Available",
            body=update.summary[:150],
            url=update.release_url,
            category="upgrade",
        )

    def _send_sms(self, update: UpdateInfo, user_id: str, pref: AlertPreference):
        """Send SMS for critical updates only."""
        if update.severity != Severity.CRITICAL:
            return  # Only critical updates warrant SMS

        from keprix.notifications.sms import send_sms

        send_sms(
            to=self._get_user_phone(user_id),
            message=(
                f"KEPRIX {update.new_version} CRITICAL UPDATE: "
                f"{update.summary[:100]}; {update.release_url}"
            ),
        )

    # ── Subscriber Management ──────────────────────────────

    def subscribe(self, user_id: str, preferences: List[AlertPreference]):
        """Register a user for update notifications."""
        self._subscribers[user_id] = preferences

    def unsubscribe(self, user_id: str, channel: Optional[AlertChannel] = None):
        """Remove a user or a specific channel."""
        if channel:
            if user_id in self._subscribers:
                self._subscribers[user_id] = [
                    p for p in self._subscribers[user_id]
                    if p.channel != channel
                ]
        else:
            self._subscribers.pop(user_id, None)

    def update_preferences(self, user_id: str, preferences: List[AlertPreference]):
        """Update notification preferences for a user."""
        self._subscribers[user_id] = preferences

    # ── Utilities ──────────────────────────────────────────

    def _already_alerted(self, update: UpdateInfo) -> bool:
        return str(update.new_version) in self._alerts_sent

    def _in_quiet_hours(self, pref: AlertPreference) -> bool:
        if pref.quiet_hours_start is None or pref.quiet_hours_end is None:
            return False
        now = datetime.now().hour
        if pref.quiet_hours_start <= pref.quiet_hours_end:
            return pref.quiet_hours_start <= now <= pref.quiet_hours_end
        else:
            # Wraps midnight (e.g., 23-07)
            return now >= pref.quiet_hours_start or now <= pref.quiet_hours_end

    def _load_state(self) -> dict:
        if self.state_file.exists():
            return json.loads(self.state_file.read_text())
        return {}

    def _save_state(self):
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.state_file.write_text(json.dumps(self._alerts_sent, indent=2))

    # ── User data helpers (implement based on product's user system) ──

    def _get_user_email(self, user_id: str) -> str:
        """Resolve user ID to email. Override per product."""
        raise NotImplementedError

    def _get_user_phone(self, user_id: str) -> str:
        """Resolve user ID to phone. Override per product."""
        raise NotImplementedError

    def _get_slack_webhook(self, user_id: str) -> Optional[str]:
        """Resolve team/user Slack webhook URL."""
        raise NotImplementedError

    def _get_discord_webhook(self, user_id: str) -> Optional[str]:
        """Resolve team/user Discord webhook URL."""
        raise NotImplementedError

    def _get_custom_webhook(self, user_id: str) -> Optional[str]:
        """Resolve custom webhook URL."""
        raise NotImplementedError


# ── Event Bus (for in-app notifications) ──────────────────

# keprix/upgrade/events.py

import threading
from typing import Callable, Dict, List

_listeners: Dict[str, List[Callable]] = {}
_lock = threading.Lock()


def on_event(event_type: str, callback: Callable):
    """Register a listener for an event type."""
    with _lock:
        _listeners.setdefault(event_type, []).append(callback)


def emit_update_event(event_type: str, data: dict):
    """Emit an event to all registered listeners."""
    with _lock:
        for cb in _listeners.get(event_type, []):
            try:
                cb(data)
            except Exception as e:
                print(f"[EventBus] Listener error for {event_type}: {e}")
```

---

## 4. In-App Notification UI Components

### 4.1 Update Banner

Appears as a non-intrusive banner at the top of the product UI.

```
┌──────────────────────────────────────────────────────────────────┐
│   Keprix 0.7.0 is available; 7 new features, 0 breaking changes│
│                                               [Review] [Upgrade] │
└──────────────────────────────────────────────────────────────────┘
```

Severity variants:

| Severity | Icon | Color | Banner Text |
|----------|------|-------|-------------|
| CRITICAL |  | Red (#EF4444) | "Critical security update; upgrade immediately" |
| HIGH | WARNING:  | Orange (#F97316) | "Important update available; includes breaking change fixes" |
| MEDIUM |  | Blue (#3B82F6) | "New Keprix version available; 7 new features" |
| LOW |  | Gray (#6B7280) | "Minor update available; bug fixes and improvements" |
| INFO | ℹ | Light Gray | "Keprix release notes available" |

### 4.2 Notification Bell

Bell icon in the header with a badge count.

```
┌──────────────────────────────────────────────────┐
│  AbbiS                            3     User │
│  ────────────────────────────────────────────────│
│                                                  │
│         (bell dropdown when clicked)             │
│  ┌──────────────────────────────────────────┐    │
│  │  CRITICAL: Keprix 0.7.1 security fix │    │
│  │    CVE-2026-1234; RCE in provider API   │    │
│  │    [Upgrade Now]                         │    │
│  │ ──────────────────────────────────────── │    │
│  │  Keprix 0.7.0 new features            │    │
│  │    A2A, Notion, Spend Tracking           │    │
│  │    [Review]  [Dismiss]                   │    │
│  │ ──────────────────────────────────────── │    │
│  │  Keprix 0.6.5 patch notes             │    │
│  │    Fixed provider timeout on slow conn    │    │
│  │    [See details]                         │    │
│  └──────────────────────────────────────────┘    │
└──────────────────────────────────────────────────┘
```

### 4.3 Notification Preferences Panel

Users configure what they want and when.

```
┌──────────────────────────────────────────────────────────────┐
│  Notification Preferences                          [Save]    │
│                                                              │
│  Channels                                                     │
│  ┌──────────────────────────────────────────────────────┐    │
│  │  In-app banner    Min severity: [Medium ▼]          │    │
│  │  Email digest     Min severity: [Low ▼]   [Daily ▼] │    │
│  │  Slack            Min severity: [High ▼]            │    │
│  │  Discord          Min severity: [Medium ▼]          │    │
│  │  Push (mobile)    Min severity: [Critical ▼]        │    │
│  │  SMS              Min severity: [Critical ▼]        │    │
│  └──────────────────────────────────────────────────────┘    │
│                                                              │
│  Quiet Hours                                                 │
│  ┌──────────────────────────────────────────────────────┐    │
│  │  Don't notify between [22:00] and [07:00]           │    │
│  └──────────────────────────────────────────────────────┘    │
│                                                              │
│  Auto-Upgrade                                                │
│  ┌──────────────────────────────────────────────────────┐    │
│  │  Auto-install security patches (CRITICAL only)      │    │
│  │  Auto-install all updates (not recommended)          │    │
│  │    Schedule: [Sunday 3:00 AM ▼]                       │    │
│  └──────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────┘
```

---

## 5. GUI Upgrade Wizard

### 5.1 Step-by-Step Wizard

The GUI upgrade flow makes the CLI `keprix upgrade --to X` accessible to non-developers.

```
┌──────────────────────────────────────────────────────────────────┐
│  Upgrade AbbiS to Keprix 0.7.0                           []    │
│                                                                  │
│  ┌─ Step 1: Compatibility Check ───────────────────── Done:  ──────┐ │
│  │  Done:  Keprix 0.7.0 is compatible with AbbiS v1.2.0            │ │
│  │  Done:  0 breaking changes                                       │ │
│  │  Done:  All features backward-compatible                         │ │
│  └──────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  ┌─ Step 2: Test Suite ───────────────────────────── Done:  ──────┐ │
│  │  Done:  247/247 tests passed                                     │ │
│  │  WARNING:   3 deprecation warnings (non-blocking)                   │ │
│  │  ⏱  Completed in 12.4 seconds                                │ │
│  │  [View Test Details]                                         │ │
│  └──────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  ┌─ Step 3: Backup ──────────────────────────────── Done:  ──────┐ │
│  │  Done:  Snapshot created: 2.3 MB                                 │ │
│  │   .keprix/upgrade/backups/pre-0.7.0-20260702T143022/       │ │
│  │  This backup can restore AbbiS to its current state.         │ │
│  └──────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  ┌─ Step 4: Install ─────────────────────────────── ⏳ ──────┐ │
│  │  ████████████████░░░░░░░░░░  67%                            │ │
│  │  Downloading keprix-0.7.0.tar.gz (4.2 MB)...                 │ │
│  │  Installing dependencies...                                  │ │
│  │  Estimated time remaining: 18 seconds                        │ │
│  └──────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  ┌─ Step 5: Migrate Config ──────────────────────── ⏸ ──────┐ │
│  │  Waiting for install to complete...                          │ │
│  └──────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  ┌─ Step 6: Verify ──────────────────────────────── ⏸ ──────┐ │
│  │  Waiting for migration to complete...                        │ │
│  └──────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  [Pause Upgrade]  [Cancel & Rollback]                            │
└──────────────────────────────────────────────────────────────────┘
```

### 5.2 Success State

```
┌──────────────────────────────────────────────────────────────────┐
│   Upgrade Complete!                                    []    │
│                                                                  │
│  AbbiS is now running on Keprix 0.7.0                            │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │  What's New                                               │    │
│  │                                                           │    │
│  │   A2A Protocol; agent-to-agent communication  │    │
│  │   Audit Dashboard; web UI for governance         │    │
│  │   Semantic Cache; free repeated LLM calls       │    │
│  │   Spend Tracking; per-session cost analytics    │    │
│  │   Proxy Pool; auto-refreshing free proxies  │    │
│  │   Notion Integration; read/write Notion pages       │    │
│  │   CLI Auto-Config; detect external tools         │    │
│  │                                                           │    │
│  │  0 breaking changes | ⏱ 46 seconds |  Backup saved    │    │
│  └──────────────────────────────────────────────────────────┘    │
│                                                                  │
│  [Enable New Features]  [View Changelog]  [Close]                │
└──────────────────────────────────────────────────────────────────┘
```

### 5.3 Failure State

```
┌──────────────────────────────────────────────────────────────────┐
│  Failed:  Upgrade Failed                                       []    │
│                                                                  │
│  ┌─ Step 1: Compatibility Check ───────────────────── Done:  ──────┐ │
│  ┌─ Step 2: Test Suite ───────────────────────────── Done:  ──────┐ │
│  ┌─ Step 3: Backup ──────────────────────────────── Done:  ──────┐ │
│  ┌─ Step 4: Install ─────────────────────────────── Failed:  ──────┐ │
│  │  Failed: Dependency conflict; keprix requires              │ │
│  │  httpx>=0.28, but abbis pins httpx==0.27.1                  │ │
│  │                                                              │ │
│  │  Suggested fix: Update abbis/pyproject.toml to allow         │ │
│  │  httpx>=0.27 without an upper bound.                         │ │
│  └──────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  AbbiS has been restored to its previous state.                  │
│  No changes were made. Your backup is at:                        │
│   .keprix/upgrade/backups/pre-0.7.0-20260702T143022/           │
│                                                                  │
│  [Show Full Error Log]  [Contact Support]  [Close]               │
└──────────────────────────────────────────────────────────────────┘
```

### 5.4 Rollback Confirmation

```
┌──────────────────────────────────────────────────────────────────┐
│  WARNING:   Rollback to Keprix 0.3.0?                          []    │
│                                                                  │
│  This will restore AbbiS to exactly how it was before the        │
│  upgrade. Any features added by Keprix 0.7.0 will be unavailable.│
│                                                                  │
│  ┌──────────────────────────────────────────────────────────────┐│
│  │  What stays:                                                 ││
│  │  Done:  Your data (deals, contacts, pipeline)                    ││
│  │  Done:  Your billing config and subscriptions                    ││
│  │  Done:  Your personas and skill packs                            ││
│  │  Done:  Your integrations (Salesforce, HubSpot)                  ││
│  │                                                              ││
│  │  What reverts:                                               ││
│  │  WARNING:   A2A Protocol; agent-to-agent disabled                 ││
│  │  WARNING:   Notion pages; integration removed                     ││
│  │  WARNING:   Spend tracking; cost analytics gone                   ││
│  │  WARNING:   Audit dashboard; governance UI removed                ││
│  └──────────────────────────────────────────────────────────────┘│
│                                                                  │
│  Estimated rollback time: ~5 seconds                             │
│                                                                  │
│  [Cancel]  [Rollback to Keprix 0.3.0]                            │
└──────────────────────────────────────────────────────────────────┘
```

---

## 6. Upgrade Scheduler (Set-and-Forget)

Many users want upgrades to happen automatically; especially security patches. The scheduler lets them pick a maintenance window.

```
┌──────────────────────────────────────────────────────────────────┐
│  Scheduled Upgrade                                        []    │
│                                                                  │
│  Auto-upgrade policy                                             │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │  ○ Manual only; I'll upgrade when I want to             │    │
│  │  ● Security patches only; auto-install CRITICAL updates │    │
│  │  ○ All updates; keep everything current                 │    │
│  └──────────────────────────────────────────────────────────┘    │
│                                                                  │
│  Maintenance window                                              │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │  Day:      [Sunday ▼]                                    │    │
│  │  Time:     [03:00 ▼] UTC                                 │    │
│  │   Only upgrade if all tests pass                        │    │
│  │   Send email notification after upgrade                 │    │
│  └──────────────────────────────────────────────────────────┘    │
│                                                                  │
│  Next scheduled check: Sunday, July 5, 2026 at 03:00 UTC        │
│                                                                  │
│  [Save]  [Cancel]                                                │
└──────────────────────────────────────────────────────────────────┘
```

The scheduler backend:

```python
# keprix/upgrade/scheduler.py

import asyncio
from datetime import datetime, timedelta
from typing import Optional


class UpgradeScheduler:
    """
    Scheduled auto-upgrade with configurable policy.

    Policies:
      - manual: Never auto-upgrade. User must initiate.
      - security_only: Auto-install CRITICAL severity updates.
      - all_updates: Auto-install everything (aggressive, not recommended).
    """

    def __init__(self, notifier: UpdateNotifier):
        self.notifier = notifier
        self.policy = "manual"
        self.maintenance_window_day = 6      # Sunday (0=Mon, 6=Sun)
        self.maintenance_window_hour = 3     # 3 AM UTC
        self.require_tests_pass = True
        self.notify_after_upgrade = True

    async def run(self):
        """Main loop; check policy, find updates, apply."""
        while True:
            now = datetime.utcnow()

            if self._in_maintenance_window(now):
                updates = await self._fetch_updates_sorted()

                for update in updates:
                    if self._should_auto_apply(update):
                        await self._auto_upgrade(update)

            # Sleep until next check (check every 30 minutes)
            await asyncio.sleep(1800)

    def _in_maintenance_window(self, now: datetime) -> bool:
        return (
            now.weekday() == self.maintenance_window_day
            and now.hour == self.maintenance_window_hour
        )

    def _should_auto_apply(self, update) -> bool:
        if self.policy == "manual":
            return False
        if self.policy == "security_only":
            return update.severity.value == "critical"
        if self.policy == "all_updates":
            return update.compatible and update.risk_level != "high"
        return False

    async def _auto_upgrade(self, update):
        """Perform unattended upgrade."""
        print(f"[Auto-Upgrade] Installing Keprix {update.new_version}...")

        # Dry run first (required)
        if self.require_tests_pass:
            success = await self._run_dry_run(update)
            if not success:
                print(f"[Auto-Upgrade] Tests failed. Skipping.")
                self._notify_upgrade_skipped(update, "tests_failed")
                return

        # Execute upgrade
        try:
            await self._execute_upgrade(update)
            if self.notify_after_upgrade:
                self._notify_upgrade_success(update)
        except Exception as e:
            print(f"[Auto-Upgrade] Failed: {e}")
            self._notify_upgrade_failed(update, str(e))
            await self._rollback()
```

---

## 7. Release Notes Viewer

Before upgrading, users want to see what's changing. The GUI release notes viewer:

```
┌──────────────────────────────────────────────────────────────────┐
│  Keprix 0.7.0; Release Notes                           []    │
│  Released: July 1, 2026                                         │
│                                                                  │
│  ┌─ Breaking Changes (0) ──────────────────────────────────────┐ │
│  │  None. This is a safe upgrade.                               │ │
│  └──────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  ┌─ New Features (7) ──────────────────────────────────────────┐ │
│  │                                                              │ │
│  │   A2A Protocol                                           │ │
│  │     Agents can now communicate directly. Delegate tasks      │ │
│  │     to other Keprix agents and receive results.              │ │
│  │     → Requires config: config/a2a.yaml                       │ │
│  │     → Opt-in feature (enable in keprix.yaml)                 │ │
│  │                                                              │ │
│  │   Semantic Prompt Cache                                    │ │
│  │     Repeated or similar prompts are served from cache.        │ │
│  │     Typical savings: 15-30% on LLM costs.                    │ │
│  │     → Enabled by default                                     │ │
│  │                                                              │ │
│  │   Spend Tracking Dashboard                                  │ │
│  │     Per-agent, per-session, per-provider cost breakdown.      │ │
│  │     → Dashboard: /admin/spend                                │ │
│  │                                                              │ │
│  │  ... (4 more)                                                │ │
│  └──────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  ┌─ Deprecations (1) ──────────────────────────────────────────┐ │
│  │  WARNING:   billing.create_invoice() → use billing.invoice.create()│ │
│  │     Deprecated in 0.7.0, will be removed in 0.9.0.           │ │
│  │     AbbiS uses this in 3 places → see migration guide.      │ │
│  └──────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  ┌─ Bug Fixes (4) ─────────────────────────────────────────────┐ │
│  │  BUG:  Provider timeout increased from 30s → 120s              │ │
│  │  BUG:  Fixed memory leak in WebSocket agent connections         │ │
│  │  BUG:  Fixed race condition in parallel tool execution          │ │
│  │  BUG:  Fixed billing webhook signature verification            │ │
│  └──────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  [Upgrade to 0.7.0]  [Skip This Version]  [Close]               │
└──────────────────────────────────────────────────────────────────┘
```

---

## 8. Email Notification Templates

### 8.1 Critical Security Update

```
Subject:  CRITICAL: Keprix 0.7.1; Security Update for AbbiS

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Keprix 0.7.1 fixes a critical security vulnerability (CVE-2026-1234).

Severity: CRITICAL
Risk: Remote code execution via provider API

AFFECTED: AbbiS v1.2.0 (running Keprix 0.3.0-0.7.0)

ACTION REQUIRED: Upgrade immediately.

Estimated time: 45 seconds
Breaking changes: None
Tests: 247/247 pass

[Upgrade Now →]
[View CVE-2026-1234 Details →]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
This is an automated alert from AbbiS.
Manage notifications: [Preferences]
```

### 8.2 Feature Update Digest (Weekly)

```
Subject:  This Week in Keprix; 0.7.0 With 7 New Features

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Keprix 0.7.0 is now available for AbbiS.

What's New:
   A2A Protocol; agent-to-agent communication
   Semantic Cache; save 15-30% on LLM costs
   Spend Dashboard; per-agent cost analytics
   Notion Integration; read/write pages
  ... and 3 more

  WARNING:   1 deprecation (no action needed until 0.9.0)
  Done:   0 breaking changes
  Done:   247/247 tests pass

[Review Full Release Notes →]
[Upgrade Now (~46 seconds) →]
[Schedule for Sunday 3 AM →]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
AbbiS · VERLOX LTD
Manage: [Notification Preferences] · [Unsubscribe]
```

---

## 9. Admin Dashboard; Upgrade Status

For product admins managing multiple instances:

```
┌──────────────────────────────────────────────────────────────────┐
│  Admin Dashboard; Upgrade Status                                │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────────┐│
│  │ Environment     Current   Available   Status                 ││
│  ├──────────────────────────────────────────────────────────────┤│
│  │ Production      0.6.5     0.7.0       WARNING:  Update available   ││
│  │ Staging         0.7.0     0.7.0       Done:  Up to date         ││
│  │ Dev (malike)    0.7.0     0.7.1-rc2    Pre-release       ││
│  │ Dev (laud)      0.6.0     0.7.0        Behind by 1 major ││
│  └──────────────────────────────────────────────────────────────┘│
│                                                                  │
│  Rollout Plan                                                    │
│  ┌──────────────────────────────────────────────────────────────┐│
│  │ 1. Dev → Already on 0.7.0                  Done:                ││
│  │ 2. Staging → Already on 0.7.0               Done:                ││
│  │ 3. Production → Scheduled: Sunday 3 AM      ⏳               ││
│  │    [Upgrade Now]  [Reschedule]  [Cancel]                     ││
│  └──────────────────────────────────────────────────────────────┘│
│                                                                  │
│  Recent Upgrades                                                 │
│  ┌──────────────────────────────────────────────────────────────┐│
│  │ Jul 5   Staging     0.6.5 → 0.7.0    Done:   46s   auto         ││
│  │ Jul 3   Dev (laud)  0.5.0 → 0.6.0    Done:   32s   manual       ││
│  │ Jun 28  Production  0.6.0 → 0.6.5    Done:   18s   auto (sec)   ││
│  └──────────────────────────────────────────────────────────────┘│
└──────────────────────────────────────────────────────────────────┘
```

---

## 10. API Endpoints

For headless deployments, CI/CD, or custom integrations:

```
GET  /api/keprix/upgrade/check          → { update_available, version, severity, ... }
GET  /api/keprix/upgrade/status         → { current_version, updates, last_check }
POST /api/keprix/upgrade/dry-run        → { passed, total_tests, failed_tests, ... }
POST /api/keprix/upgrade/execute        → { status: "in_progress" | "success" | "failed" }
POST /api/keprix/upgrade/rollback       → { status, restored_version }
GET  /api/keprix/upgrade/history        → [{ from, to, date, status }]
GET  /api/keprix/upgrade/changelog      → [{ version, entries }]

# Notification preferences
GET  /api/keprix/notifications/preferences  → [{ channel, min_severity, ... }]
PUT  /api/keprix/notifications/preferences  → Update preferences
POST /api/keprix/notifications/test         → Send test notification
```

---

## 11. Implementation Checklist

| # | Component | Description |
|---|-----------|-------------|
| 1 | `keprix/upgrade/notifier.py` | UpdateNotifier; polls, classifies, dispatches |
| 2 | `keprix/upgrade/events.py` | Event bus for in-app notifications |
| 3 | `keprix/upgrade/scheduler.py` | Auto-upgrade scheduler with maintenance windows |
| 4 | `keprix/upgrade/email_templates/` | HTML email templates for each severity |
| 5 | `keprix/upgrade/slack_discord.py` | Slack/Discord webhook formatters |
| 6 | `keprix/upgrade/gui/` | GUI upgrade wizard components |
| 7 | `keprix/upgrade/api.py` | REST API endpoints for headless upgrades |
| 8 | `keprix/upgrade/changelog_viewer.py` | Release notes viewer component |
| 9 | `keprix/notifications/email.py` | Email delivery (Resend, SendGrid, SES) |
| 10 | `keprix/notifications/push.py` | Push notification delivery |
| 11 | `keprix/notifications/sms.py` | SMS delivery (Twilio, etc.) |
| 12 | `keprix/dashboard/upgrade_status.py` | Admin dashboard upgrade status page |
| 13 | Product integration guides | How AbbiS/Petraclus/FleetZ wire in the GUI |

---

## 12. Summary

| Concern | Solution |
|---------|----------|
| "How do I know there's an update?" | In-app banner, bell badge, email digest |
| "Is it urgent?" | Severity classifier; CRITICAL (red) to INFO (gray) |
| "Will it break anything?" | Pre-check compatibility, show breaking changes |
| "Can I review before upgrading?" | Release notes viewer with changelog, risk level |
| "I'm not technical" | GUI upgrade wizard; 6 steps with progress bar |
| "I want it automatic" | Scheduler; "security patches at 3 AM Sunday" |
| "What if it fails?" | Auto-rollback, friendly error message, support link |
| "Can my team see status?" | Admin dashboard with multi-environment view |
| "Can I integrate with my stack?" | REST API + Slack/Discord/Webhook channels |
| "Don't bother me at night" | Quiet hours; mute notifications 22:00-07:00 |

**No more surprise upgrades. No more upgrade anxiety. One click, 46 seconds, done.**
