"""Browser action engine."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from keprix.browser.action_log import get_action_log
from keprix.browser.drivers import BrowserDriver, create_browser_driver
from keprix.browser.safety import classify_action, redact_metadata, redact_text, requires_approval
from keprix.browser.screenshots import screenshot_store
from keprix.browser.world_model import build_world_state


@dataclass
class BrowserSession:
    session_id: str
    objective: str
    driver: BrowserDriver
    pending_approval: dict[str, Any] | None = None
    screenshots: dict[str, bytes] = field(default_factory=dict)


class ActionEngine:
    def __init__(self) -> None:
        self._sessions: dict[str, BrowserSession] = {}

    def create_session(
        self,
        *,
        objective: str,
        url: str = "about:blank",
        driver: BrowserDriver | None = None,
        session_id: str | None = None,
    ) -> BrowserSession:
        session_id = session_id or str(uuid.uuid4())
        resolved = driver or create_browser_driver()
        resolved.navigate(url)
        session = BrowserSession(session_id=session_id, objective=objective, driver=resolved)
        self._sessions[session_id] = session
        return session

    def get(self, session_id: str) -> BrowserSession | None:
        return self._sessions.get(session_id)

    def propose_actions(self, session_id: str) -> dict[str, Any]:
        session = self._require(session_id)
        snapshot = session.driver.snapshot()
        world = build_world_state(snapshot, session.objective)
        proposals = [
            {"action": "read_page", "selector": "", "risk": "safe"},
        ]
        for element in world["visible_elements"][:5]:
            role = str(element.get("role") or "")
            element_id = str(element.get("id") or element.get("element_id") or "")
            if role in {"textbox", "searchbox", "input"}:
                proposals.append({"action": "fill", "selector": element_id, "risk": "safe"})
            if role in {"button", "submit"}:
                proposals.append(
                    {
                        "action": "submit" if "submit" in element_id.lower() else "click",
                        "selector": element_id,
                        "risk": classify_action("submit" if "submit" in element_id.lower() else "click"),
                    }
                )
        if len(proposals) == 1:
            proposals.extend(
                [
                    {"action": "fill", "selector": "search", "risk": "safe"},
                    {"action": "submit", "selector": "submit", "risk": "approval_required"},
                ]
            )
        return {"world": world, "proposals": proposals}

    def run_action(
        self,
        session_id: str,
        *,
        action: str,
        selector: str = "",
        value: str = "",
        approved: bool = False,
    ) -> dict[str, Any]:
        session = self._require(session_id)
        risk = classify_action(action, selector=selector)
        if requires_approval(action) and not approved:
            before_id = self._store_screenshot(session)
            session.pending_approval = {"action": action, "selector": selector, "value": value}
            get_action_log().append(
                session_id=session_id,
                action=action,
                selector=redact_text(selector),
                status="awaiting_approval",
                screenshot_id=before_id,
                metadata=redact_metadata({"phase": "before", "value": value}),
            )
            return {"status": "awaiting_approval", "action": action, "screenshot_id": before_id}
        if action == "navigate":
            snapshot = session.driver.navigate(value or selector)
        elif action == "click":
            snapshot = session.driver.click(selector)
        elif action == "fill":
            snapshot = session.driver.fill(selector, value)
        elif action == "read_page":
            snapshot = session.driver.snapshot()
        else:
            snapshot = session.driver.snapshot()
        after_id = self._store_screenshot(session)
        get_action_log().append(
            session_id=session_id,
            action=action,
            selector=redact_text(selector),
            status="executed",
            screenshot_id=after_id,
            metadata=redact_metadata({"phase": "after", "value": value}),
        )
        session.pending_approval = None
        return {
            "status": "executed",
            "risk": risk,
            "world": build_world_state(snapshot, session.objective),
            "screenshot_id": after_id,
        }

    def approve_pending(self, session_id: str) -> dict[str, Any]:
        session = self._require(session_id)
        pending = session.pending_approval
        if not pending:
            return {"status": "nothing_pending"}
        return self.run_action(
            session_id,
            action=pending["action"],
            selector=pending.get("selector", ""),
            value=pending.get("value", ""),
            approved=True,
        )

    def list_actions(self, session_id: str) -> list[dict[str, Any]]:
        return [row.to_dict() for row in get_action_log().list_for_session(session_id)]

    def get_screenshot(self, session_id: str, screenshot_id: str) -> bytes | None:
        session = self._sessions.get(session_id)
        if session is None:
            return None
        if screenshot_id in session.screenshots:
            return session.screenshots[screenshot_id]
        stored = screenshot_store.get(screenshot_id)
        return stored.data if stored else None

    def _store_screenshot(self, session: BrowserSession) -> str:
        shot = screenshot_store.save(session.driver.screenshot())
        session.screenshots[shot.id] = shot.data
        return shot.id

    def _require(self, session_id: str) -> BrowserSession:
        session = self._sessions.get(session_id)
        if session is None:
            raise KeyError(session_id)
        return session


_engine = ActionEngine()


def get_action_engine() -> ActionEngine:
    return _engine
