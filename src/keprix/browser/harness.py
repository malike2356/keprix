"""Browser-use style harness for coding agents."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from keprix.browser.action_engine import ActionEngine, get_action_engine
from keprix.browser.browser_profile import BrowserProfile, ProfileKind, get_profile_store
from keprix.browser.cloud_executor import get_cloud_executor
from keprix.browser.drivers import BrowserDriver, StubBrowserDriver, create_browser_driver
from keprix.browser.element_map import element_map_from_snapshot
from keprix.browser.screenshots import screenshot_store
from keprix.browser.session_store import HarnessSessionRecord, get_session_store


@dataclass
class HarnessSnapshot:
    session_id: str
    trace_id: str
    url: str
    title: str
    dom_snapshot: str
    accessibility_tree: list[dict[str, Any]]
    screenshot_id: str | None
    console_logs: list[dict[str, Any]] = field(default_factory=list)
    network_summary: list[dict[str, Any]] = field(default_factory=list)
    download_events: list[dict[str, Any]] = field(default_factory=list)
    upload_controls: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "trace_id": self.trace_id,
            "url": self.url,
            "title": self.title,
            "dom_snapshot": self.dom_snapshot,
            "accessibility_tree": self.accessibility_tree,
            "screenshot_id": self.screenshot_id,
            "console_logs": self.console_logs,
            "network_summary": self.network_summary,
            "download_events": self.download_events,
            "upload_controls": self.upload_controls,
        }


class BrowserHarness:
    """Dependable browser surface for agents: page state, DOM, a11y, logs, uploads."""

    def __init__(
        self,
        *,
        session_id: str,
        trace_id: str,
        driver: BrowserDriver,
        engine: ActionEngine,
        profile: BrowserProfile | None = None,
        read_only: bool = False,
    ) -> None:
        self.session_id = session_id
        self.trace_id = trace_id
        self.driver = driver
        self.engine = engine
        self.profile = profile
        self.read_only = read_only
        self.console_logs: list[dict[str, Any]] = []
        self.network_summary: list[dict[str, Any]] = []
        self.download_events: list[dict[str, Any]] = []

    def navigate(self, url: str) -> HarnessSnapshot:
        if self.read_only and url not in ("about:blank", self.driver.snapshot().url):
            raise PermissionError("Read-only profile cannot navigate to new URLs")
        snapshot = self.driver.navigate(url)
        self._record_network("document", url, 200)
        return self.capture()

    def capture(self) -> HarnessSnapshot:
        page = self.driver.snapshot()
        elements = element_map_from_snapshot(page)
        dom_lines = [f"<{item.role} id='{item.element_id}'>{item.label}</{item.role}>" for item in elements]
        a11y = [
            {
                "role": item.role,
                "name": item.label,
                "id": item.element_id,
                "iframe_path": item.iframe_path,
            }
            for item in elements
        ]
        upload_controls = [
            item.to_dict()
            for item in elements
            if item.role in {"file", "input"} or "upload" in item.label.lower()
        ]
        shot = screenshot_store.save(self.driver.screenshot())
        session = self.engine.get(self.session_id)
        if session is not None:
            session.screenshots[shot.id] = shot.data
        return HarnessSnapshot(
            session_id=self.session_id,
            trace_id=self.trace_id,
            url=page.url,
            title=page.title,
            dom_snapshot="\n".join(dom_lines) or page.text[:2000],
            accessibility_tree=a11y,
            screenshot_id=shot.id,
            console_logs=list(self.console_logs),
            network_summary=list(self.network_summary),
            download_events=list(self.download_events),
            upload_controls=upload_controls,
        )

    def record_console(self, level: str, message: str) -> None:
        self.console_logs.append({"level": level, "message": message})

    def record_download(self, filename: str, *, url: str = "") -> None:
        self.download_events.append({"filename": filename, "url": url})

    def _record_network(self, kind: str, url: str, status: int) -> None:
        self.network_summary.append({"kind": kind, "url": url, "status": status})


class HarnessManager:
    def __init__(self) -> None:
        self._harnesses: dict[str, BrowserHarness] = {}

    def open_session(
        self,
        *,
        workspace_id: str,
        objective: str,
        url: str = "about:blank",
        profile_id: str | None = None,
        driver: BrowserDriver | None = None,
    ) -> tuple[BrowserHarness, HarnessSessionRecord]:
        profile_store = get_profile_store()
        profile = profile_store.get(profile_id, workspace_id) if profile_id else None
        read_only = profile.read_only if profile else False

        if profile and profile.kind == ProfileKind.DISPOSABLE:
            resolved_driver = StubBrowserDriver()
        else:
            resolved_driver = driver or create_browser_driver()

        engine = get_action_engine()
        record = get_session_store().create(
            workspace_id=workspace_id,
            objective=objective,
            url=url,
            profile_id=profile_id,
            metadata={
                "profile_kind": profile.kind.value if profile else ProfileKind.FRESH.value,
                "mode": "dry_run" if (profile and profile.kind == ProfileKind.DISPOSABLE) or isinstance(resolved_driver, StubBrowserDriver) else "live",
            },
        )
        session = engine.create_session(
            objective=objective,
            url=url,
            driver=resolved_driver,
            session_id=record.session_id,
        )

        cloud = get_cloud_executor().create_remote_session(f"harness-{record.session_id}")
        if cloud:
            record.metadata["cloud_session"] = cloud

        harness = BrowserHarness(
            session_id=session.session_id,
            trace_id=record.trace_id,
            driver=resolved_driver,
            engine=engine,
            profile=profile,
            read_only=read_only,
        )
        self._harnesses[session.session_id] = harness
        harness.capture()
        return harness, record

    def get(self, session_id: str) -> BrowserHarness | None:
        return self._harnesses.get(session_id)

    def list_sessions(self, workspace_id: str) -> list[dict[str, Any]]:
        return [row.to_dict() for row in get_session_store().list_for_workspace(workspace_id)]


_manager: HarnessManager | None = None


def get_harness_manager() -> HarnessManager:
    global _manager
    if _manager is None:
        _manager = HarnessManager()
    return _manager
