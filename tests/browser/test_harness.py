"""Browser harness tests."""

from keprix.browser.drivers import StubBrowserDriver
from keprix.browser.harness import BrowserHarness, get_harness_manager


def test_harness_capture_includes_dom_and_a11y() -> None:
    manager = get_harness_manager()
    harness, record = manager.open_session(
        workspace_id="ws-1",
        objective="inspect page",
        url="https://example.com",
        driver=StubBrowserDriver(),
    )
    snap = harness.capture()
    assert snap.session_id == record.session_id
    assert snap.trace_id == record.trace_id
    assert "search" in snap.dom_snapshot.lower() or snap.accessibility_tree
    assert snap.screenshot_id
    assert isinstance(snap.network_summary, list)


def test_agent_can_open_harness_session() -> None:
    harness, record = get_harness_manager().open_session(
        workspace_id="coding-agent",
        objective="read dashboard",
        driver=StubBrowserDriver(),
    )
    assert harness.session_id
    assert record.workspace_id == "coding-agent"
    listed = get_harness_manager().list_sessions("coding-agent")
    assert any(row["session_id"] == harness.session_id for row in listed)
