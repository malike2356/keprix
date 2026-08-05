from keprix.tui.command_center.status import StatusSnapshot, render_status_bar, segment


def test_status_bar_width_is_stable_across_updates() -> None:
    first = render_status_bar(StatusSnapshot(model="mini", provider="local"), width=96)
    second = render_status_bar(
        StatusSnapshot(
            model="very-long-model-name-that-should-not-resize-the-bar",
            provider="very-long-provider",
            token_count=999999,
            latency_ms=123456,
        ),
        width=96,
    )

    assert len(first) == 96
    assert len(second) == 96


def test_segment_truncates_predictably() -> None:
    rendered = segment("model", "abcdefghijklmnopqrstuvwxyz", width=12)

    assert len(rendered) == 12
    assert rendered.endswith("~")
