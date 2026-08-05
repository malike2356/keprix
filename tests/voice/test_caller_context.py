import pytest

from keprix.voice.caller_context import CallerContext, reset_caller_memory
from keprix.voice.providers.llm.keprix_agent import KeprixVoiceAgent
from keprix.voice.session import create_voice_session, reset_voice_sessions


@pytest.fixture(autouse=True)
def reset_state() -> None:
    reset_voice_sessions()
    reset_caller_memory()


@pytest.mark.asyncio
async def test_caller_memory_feeds_welcome_back_response() -> None:
    caller = "+155501"
    context = await CallerContext.from_phone(caller)
    context.name = "Sarah"
    session = create_voice_session(caller=caller, called="+155502")
    await context.save_summary(session, outcome="resolved", notes="asked about a valuation")

    loaded = await CallerContext.from_phone(caller)
    response = await KeprixVoiceAgent(business_name="Aiva Realty").respond("hello again", session, loaded)

    assert loaded.previous_calls
    assert "Welcome back, Sarah" in response.text
