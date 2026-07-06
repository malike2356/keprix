"""Support diagnostics tests."""

from __future__ import annotations

import pytest

from keprix.support.diagnostics import build_diagnostics_bundle, redact_bundle_text


@pytest.mark.asyncio
async def test_diagnostics_bundle_redacts_secrets(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-abcdefghijklmnopqrstuvwxyz1234")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:secretpass@localhost/db")
    bundle = await build_diagnostics_bundle(
        recent_errors=['API_KEY="sk-abcdefghijklmnopqrstuvwxyz1234"'],
        job_failures=[{"error": "token=supersecretvalue123"}],
    )
    raw = str(bundle)
    assert "sk-abcdefghijklmnopqrstuvwxyz1234" not in raw
    assert "supersecretvalue123" not in raw
    assert bundle["config_summary"].get("DATABASE_URL") == "[configured]"


def test_redact_bundle_text() -> None:
    redacted = redact_bundle_text('password="hunter2"')
    assert "hunter2" not in redacted
