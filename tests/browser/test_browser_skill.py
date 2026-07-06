"""Browser skill tests."""

import sys

import pytest

from keprix.browser.browser_skill import list_skills, run_skill
from keprix.browser.drivers import StubBrowserDriver
from keprix.browser.harness import BrowserHarness, get_harness_manager


def _harness() -> BrowserHarness:
    harness, _ = get_harness_manager().open_session(
        workspace_id="ws",
        objective="skill test",
        driver=StubBrowserDriver(),
    )
    return harness


def test_skills_declare_risk_and_approval() -> None:
    skills = {item["name"]: item for item in list_skills()}
    assert skills["checkout_dry_run"]["approval_required"] is True
    assert skills["form_filling"]["approval_required"] is False
    assert skills["report_download"]["risk"] == "high"


def test_form_filling_skill_executes() -> None:
    harness = _harness()
    result = run_skill("form_filling", harness, {"fields": {"search": "hello"}})
    assert result["status"] == "executed"
    assert "search" in result["filled"]


def test_purchase_skill_requires_approval() -> None:
    harness = _harness()
    result = run_skill("checkout_dry_run", harness, {})
    assert result["status"] == "awaiting_approval"


@pytest.mark.skipif(sys.version_info < (3, 11), reason="Playbook runtime requires Python 3.11+")
def test_skills_register_as_playbook_nodes() -> None:
    from keprix.browser.browser_skill import SKILL_REGISTRY, register_playbook_nodes
    from keprix.playbook.runtime.graph import PlaybookGraph

    graph = PlaybookGraph("browser-skills-test")
    register_playbook_nodes(graph)
    compiled = graph.compile()
    assert "browser.form_filling" in compiled.nodes
    assert len(compiled.nodes) == len(SKILL_REGISTRY)
