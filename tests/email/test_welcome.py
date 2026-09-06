from __future__ import annotations

import pytest

from keprix.email.welcome import send_welcome_email, welcome_content


def test_welcome_content_has_text_html_and_chat_cta(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KEPRIX_INSTANCE_URL", "https://app.example.test")
    content = welcome_content(recipient_name="Ada", workspace_name="Research")
    assert "https://app.example.test/chat-only" in content["text"]
    assert "https://app.example.test/chat-only" in content["html"]
    assert "Ask, Build, Connect" in content["text"]


@pytest.mark.asyncio
async def test_welcome_skips_without_email_or_when_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("KEPRIX_WELCOME_EMAIL_ENABLED", raising=False)
    no_email = await send_welcome_email(
        workspace_id="ws", workspace_name="One", user={"username": "Ada"}
    )
    disabled = await send_welcome_email(
        workspace_id="ws",
        workspace_name="One",
        user={"username": "Ada", "email": "a@example.com"},
    )
    assert no_email["reason"] == "no_email"
    assert disabled["reason"] == "sending_disabled"


@pytest.mark.asyncio
async def test_welcome_returns_provider_confirmation(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KEPRIX_WELCOME_EMAIL_ENABLED", "true")

    async def fake_send_email(*args, **kwargs):
        assert kwargs["body_html"]
        assert kwargs["body_text"]
        return "provider-123"

    monkeypatch.setattr("keprix.email.welcome.send_email", fake_send_email)
    result = await send_welcome_email(
        workspace_id="ws",
        workspace_name="One",
        user={"username": "Ada", "email": "a@example.com"},
    )
    assert result == {"status": "sent", "provider_confirmation_id": "provider-123"}
