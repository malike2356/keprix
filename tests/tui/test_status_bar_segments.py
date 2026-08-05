from keprix.tui.command_center.status import StatusSnapshot, render_status_bar, status_segments


def test_status_bar_represents_required_segments() -> None:
    snapshot = StatusSnapshot(
        model="mini",
        provider="local",
        transport="http",
        session_id="abcdef123456",
        queue_depth=2,
        busy_mode="queue",
        token_count=1234,
        latency_ms=45,
        cost_estimate=0.012,
        backend_healthy=True,
        agent_busy=True,
        voice_state="recording",
    )

    labels = [label for label, _, _ in status_segments(snapshot)]
    assert labels == [
        "health",
        "agent",
        "model",
        "provider",
        "transport",
        "session",
        "queue",
        "mode",
        "tokens",
        "latency",
        "cost",
        "voice",
    ]
    rendered = render_status_bar(snapshot, width=220)
    assert "model:mini" in rendered
    assert "provider:local" in rendered
    assert "transport:http" in rendered
    assert "session:abcdef12" in rendered
    assert "queue:2" in rendered
    assert "mode:queue" in rendered
    assert "tokens:1.2K" in rendered
    assert "latency:45ms" in rendered
    assert "cost:$0.01" in rendered
    assert "voice:recording" in rendered
