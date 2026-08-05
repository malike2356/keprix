import pytest

from keprix.voice.interruptions import InterruptionHandler
from keprix.voice.session import create_voice_session, reset_voice_sessions


@pytest.fixture(autouse=True)
def reset_sessions() -> None:
    reset_voice_sessions()


@pytest.mark.asyncio
async def test_interruption_marks_barge_in() -> None:
    session = create_voice_session(caller="+155501", called="+155502")

    await InterruptionHandler().handle(session, "sorry, can I stop you there?")

    assert session.transcript[-1]["event"] == "interrupt"
    assert session.transcript[-1]["text"] == "sorry, can I stop you there?"
