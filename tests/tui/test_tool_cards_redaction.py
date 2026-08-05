from __future__ import annotations

from keprix.tui.renderer.tool_cards import redacted_text, render_tool_card, tool_card_from_runtime


def test_tool_card_redacts_secret_args() -> None:
    card = tool_card_from_runtime(
        name="request",
        args={"api_key": "abc123", "path": "safe"},
        result="ok",
    )
    rendered = render_tool_card(card)
    assert "abc123" not in rendered
    assert "api_key='[redacted]'" in rendered
    assert "path='safe'" in rendered


def test_tool_card_redacts_secret_result_text() -> None:
    rendered = render_tool_card(
        tool_card_from_runtime(
            name="curl",
            status="done",
            result="token=abc123 authorization: BearerSecret",
        )
    )
    assert "abc123" not in rendered
    assert "BearerSecret" not in rendered
    assert "[redacted]" in rendered


def test_redacted_text_handles_password_like_values() -> None:
    assert "supersecret" not in redacted_text("password=supersecret")
