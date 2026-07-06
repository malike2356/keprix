"""Action engine tests."""

from keprix.browser.action_engine import ActionEngine
from keprix.browser.drivers import StubBrowserDriver


def test_safe_action_executes_without_approval() -> None:
    engine = ActionEngine()
    session = engine.create_session(
        objective="read page",
        driver=StubBrowserDriver(),
    )
    result = engine.run_action(session.session_id, action="read_page")
    assert result["status"] == "executed"
    assert result["screenshot_id"]


def test_risky_action_captures_before_screenshot() -> None:
    engine = ActionEngine()
    session = engine.create_session(objective="submit form", driver=StubBrowserDriver())
    pending = engine.run_action(session.session_id, action="submit", selector="submit")
    assert pending["status"] == "awaiting_approval"
    assert pending["screenshot_id"]
    approved = engine.approve_pending(session.session_id)
    assert approved["status"] == "executed"
    actions = engine.list_actions(session.session_id)
    assert any(row["status"] == "awaiting_approval" for row in actions)
    assert any(row["status"] == "executed" for row in actions)


def test_propose_actions_returns_world_model() -> None:
    engine = ActionEngine()
    session = engine.create_session(objective="search the site", driver=StubBrowserDriver())
    proposals = engine.propose_actions(session.session_id)
    assert proposals["world"]["objective"] == "search the site"
    assert proposals["proposals"]


def test_action_log_redacts_sensitive_metadata() -> None:
    engine = ActionEngine()
    session = engine.create_session(objective="fill form", driver=StubBrowserDriver())
    engine.run_action(
        session.session_id,
        action="fill",
        selector="email",
        value="password=secret123 api_key=abc",
    )
    actions = engine.list_actions(session.session_id)
    assert actions
    metadata = actions[0].get("metadata") or {}
    assert "secret123" not in str(metadata)
    assert "[REDACTED]" in str(metadata)
