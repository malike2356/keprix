"""Realtime agent lane tests."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from keprix.agents_runtime.realtime import create_session, get_session, reset_sessions
from keprix.api.main import app


@pytest.fixture(autouse=True)
def _clean_sessions():
    reset_sessions()
    yield
    reset_sessions()


def test_realtime_transcript_streams_events() -> None:
    session = create_session("echo_agent")
    session.append("speech_in", "Hello, I need help with billing")
    session.append("speech_out", "I can help with billing questions.")
    session.append("tool_pause", "apply_credit", tool="apply_credit")
    session.append("interrupt", "")
    session.append("escalation", "Escalating to text summary")

    transcript = session.transcript()
    types = [event["type"] for event in transcript]
    assert types == ["speech_in", "speech_out", "tool_pause", "interrupt", "escalation"]
    assert session.awaiting_approval is False
    assert session.interrupted is True

    loaded = get_session(session.session_id)
    assert loaded is not None
    assert len(loaded.transcript()) == 5


@pytest.mark.asyncio
async def test_realtime_api_transcript_route(monkeypatch) -> None:
    monkeypatch.setenv("KEPRIX_API_TOKEN", "test-api-token")
    headers = {"Authorization": "Bearer test-api-token"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        created = await client.post("/api/agents-runtime/realtime/sessions?agent=echo_agent", headers=headers)
        assert created.status_code == 200
        session_id = created.json()["session_id"]

        event = await client.post(
            f"/api/agents-runtime/realtime/sessions/{session_id}/events",
            headers=headers,
            json={"type": "transcript", "text": "Caller asked about invoice"},
        )
        assert event.status_code == 200

        transcript = await client.get(
            f"/api/agents-runtime/realtime/sessions/{session_id}/transcript",
            headers=headers,
        )
        assert transcript.status_code == 200
        lines = transcript.json()["transcript"]
        assert len(lines) == 1
        assert lines[0]["text"] == "Caller asked about invoice"
