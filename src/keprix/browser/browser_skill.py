"""Reusable browser skills with risk declarations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from keprix.browser.harness import BrowserHarness
from keprix.browser.safety import requires_approval


SkillHandler = Callable[[BrowserHarness, dict[str, Any]], dict[str, Any]]


@dataclass(frozen=True)
class BrowserSkill:
    name: str
    description: str
    risk: str
    approval_required: bool
    handler: SkillHandler

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "risk": self.risk,
            "approval_required": self.approval_required,
        }


def _skill_form_filling(harness: BrowserHarness, params: dict[str, Any]) -> dict[str, Any]:
    fields = params.get("fields") or {"search": "sample"}
    for selector, value in fields.items():
        harness.engine.run_action(harness.session_id, action="fill", selector=selector, value=str(value))
    return {"status": "executed", "filled": list(fields.keys())}


def _skill_account_setup(harness: BrowserHarness, params: dict[str, Any]) -> dict[str, Any]:
    harness.engine.run_action(harness.session_id, action="fill", selector="email", value=params.get("email", "user@example.com"))
    harness.engine.run_action(harness.session_id, action="fill", selector="password", value="[REDACTED]")
    return {"status": "executed", "step": "account_setup_draft"}


def _skill_dashboard_navigation(harness: BrowserHarness, params: dict[str, Any]) -> dict[str, Any]:
    target = str(params.get("path") or "/dashboard")
    harness.navigate(params.get("base_url", harness.driver.snapshot().url) + target)
    return {"status": "executed", "path": target}


def _skill_price_check(harness: BrowserHarness, params: dict[str, Any]) -> dict[str, Any]:
    query = str(params.get("query") or "pricing")
    harness.engine.run_action(harness.session_id, action="fill", selector="search", value=query)
    snap = harness.capture()
    return {"status": "executed", "query": query, "screenshot_id": snap.screenshot_id}


def _skill_report_download(harness: BrowserHarness, params: dict[str, Any]) -> dict[str, Any]:
    result = harness.engine.run_action(harness.session_id, action="download_sensitive", selector="report")
    return result


def _skill_research_collection(harness: BrowserHarness, params: dict[str, Any]) -> dict[str, Any]:
    harness.engine.run_action(harness.session_id, action="read_page")
    snap = harness.capture()
    return {
        "status": "executed",
        "url": snap.url,
        "summary": snap.dom_snapshot[:500],
        "screenshot_id": snap.screenshot_id,
    }


def _skill_checkout_dry_run(harness: BrowserHarness, params: dict[str, Any]) -> dict[str, Any]:
    harness.engine.run_action(harness.session_id, action="fill", selector="card", value="4111111111111111")
    pending = harness.engine.run_action(harness.session_id, action="purchase", selector="checkout")
    return {"status": pending.get("status"), "dry_run": True}


SKILL_REGISTRY: dict[str, BrowserSkill] = {
    "form_filling": BrowserSkill("form_filling", "Fill draft form fields", "low", False, _skill_form_filling),
    "account_setup": BrowserSkill("account_setup", "Prepare account signup form", "medium", False, _skill_account_setup),
    "dashboard_navigation": BrowserSkill("dashboard_navigation", "Navigate dashboards", "low", False, _skill_dashboard_navigation),
    "price_check": BrowserSkill("price_check", "Search and capture pricing", "low", False, _skill_price_check),
    "report_download": BrowserSkill("report_download", "Download a report file", "high", True, _skill_report_download),
    "research_collection": BrowserSkill("research_collection", "Collect visible research data", "low", False, _skill_research_collection),
    "checkout_dry_run": BrowserSkill("checkout_dry_run", "Fill checkout without purchase", "high", True, _skill_checkout_dry_run),
}


def list_skills() -> list[dict[str, Any]]:
    return [skill.to_dict() for skill in SKILL_REGISTRY.values()]


def run_skill(name: str, harness: BrowserHarness, params: dict[str, Any] | None = None) -> dict[str, Any]:
    skill = SKILL_REGISTRY.get(name)
    if skill is None:
        raise KeyError(name)
    if skill.approval_required and not params.get("approved"):
        action = "purchase" if name == "checkout_dry_run" else "download_sensitive"
        if requires_approval(action):
            return harness.engine.run_action(harness.session_id, action=action, selector=name)
    return skill.handler(harness, params or {})


def register_playbook_nodes(graph: Any) -> None:
    """Register browser skills as playbook nodes."""
    from keprix.playbook.runtime.graph import PlaybookGraph

    def _node(skill_name: str) -> Callable[[dict[str, Any]], dict[str, Any]]:
        def _handler(state: dict[str, Any]) -> dict[str, Any]:
            from keprix.browser.harness import get_harness_manager

            session_id = state.get("browser_session_id")
            if not session_id:
                raise ValueError("browser_session_id required in playbook state")
            harness = get_harness_manager().get(str(session_id))
            if harness is None:
                raise KeyError(session_id)
            result = run_skill(skill_name, harness, dict(state.get("browser_params") or {}))
            return {"browser_result": result}

        return _handler

    for skill_name in SKILL_REGISTRY:
        graph.add_node(f"browser.{skill_name}", _node(skill_name))
