from keprix.tui.command_center.status import StatusSnapshot, render_status_bar


def test_status_bar_offline_state_is_clear() -> None:
    rendered = render_status_bar(
        StatusSnapshot(
            backend_healthy=False,
            agent_busy=False,
            transport="http",
            session_id="",
            voice_state="off",
        ),
        width=120,
    )

    assert "health:OFFLINE" in rendered
    assert "agent:idle" in rendered
    assert "transport:http" in rendered
    assert "session:none" in rendered
    assert "Traceback" not in rendered
