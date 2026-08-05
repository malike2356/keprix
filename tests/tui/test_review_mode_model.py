from keprix.tui.command_center.palette import dispatch_for_action
from keprix.tui.command_center.registry import build_default_registry
from keprix.tui.command_center.review import build_review_report, render_review_report
from keprix.tui.runtime_store import RuntimeStore


def test_review_mode_model_uses_runtime_data() -> None:
    store = RuntimeStore()
    store.start_turn(session_id="s1", model="mini", provider="local")
    store.finish_tool("read_file", call_id="t1", status="done", result_preview="ok")
    store.spawn_subagent("a1", label="Reviewer")
    store.finish_subagent("a1", status="done", preview="checked")
    store.record_review_item("file_changed", "src/app.py")
    store.record_review_item("command_executed", "pytest tests/tui")
    store.record_review_item("test_run", "tests/tui")
    store.record_review_item("warning", "migration not run")
    store.record_review_item("next_action", "deploy build")
    store.update_usage({"total_tokens": 42, "cost": 0.02})
    store.finish_turn()

    report = build_review_report(store, user_request="Fix TUI", assistant_outcome="Updated review mode")
    rendered = render_review_report(report)

    assert "Fix TUI" in rendered
    assert "Updated review mode" in rendered
    assert "src/app.py" in rendered
    assert "read_file (done)" in rendered
    assert "Reviewer (done)" in rendered
    assert "pytest tests/tui" in rendered
    assert "migration not run" in rendered
    assert "deploy build" in rendered
    assert "Tokens: 42" in rendered
    assert "Cost: 0.0200" in rendered


def test_command_palette_exposes_review_action() -> None:
    action = next(item for item in build_default_registry().all() if item.id == "ui:review")
    result = dispatch_for_action(action)

    assert result.dispatch_kind == "open_review"
