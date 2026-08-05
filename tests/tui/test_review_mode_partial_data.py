from keprix.tui.command_center.review import build_review_report, render_review_report
from keprix.tui.runtime_store import RuntimeStore


def test_review_mode_partial_data_does_not_invent_facts() -> None:
    store = RuntimeStore()

    report = build_review_report(store)
    rendered = render_review_report(report)

    assert "User request\nNone recorded" in rendered
    assert "Assistant outcome\nNone recorded" in rendered
    assert "Files changed\n- None recorded" in rendered
    assert "Tools used\n- None recorded" in rendered
    assert "Tests run\n- None recorded" in rendered
    assert "Cost: None recorded" in rendered
    assert "probably" not in rendered.lower()
