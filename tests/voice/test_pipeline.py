import pytest

from keprix.voice.cost_tracker import estimate_call_cost
from keprix.voice.pipeline import VoicePipeline
from keprix.voice.providers.llm.keprix_agent import KeprixVoiceAgent
from keprix.voice.providers.stt.deepgram import DeepgramSTT
from keprix.voice.providers.tts.elevenlabs import ElevenLabsTTS
from keprix.voice.session import create_voice_session, reset_voice_sessions


async def audio_stream(text: str):
    yield text.encode("utf-8")


async def silent_stream(chunks: int):
    for _ in range(chunks):
        yield b"\x80" * 20


@pytest.fixture(autouse=True)
def reset_sessions() -> None:
    reset_voice_sessions()


@pytest.mark.asyncio
async def test_pipeline_confirms_booking_and_returns_audio() -> None:
    session = create_voice_session(caller="+155501", called="+155502")
    pipeline = VoicePipeline(stt=DeepgramSTT(), agent=KeprixVoiceAgent(), tts=ElevenLabsTTS())

    chunks = [chunk async for chunk in pipeline.run(audio_stream("book a viewing Tuesday at 2pm"), session)]

    assert chunks
    assert b"Tuesday at 2pm" in chunks[0]
    assert session.appointments_booked == 1
    assert session.transcript[-1]["action"] == "confirm_booking"


def test_five_minute_call_estimate_stays_under_target() -> None:
    assert estimate_call_cost(300)["total_usd"] < 0.20


@pytest.mark.asyncio
async def test_pipeline_prompts_after_silence() -> None:
    session = create_voice_session(caller="+155501", called="+155502")
    pipeline = VoicePipeline(
        stt=DeepgramSTT(),
        agent=KeprixVoiceAgent(),
        tts=ElevenLabsTTS(),
        silence_prompt_chunks=2,
    )

    chunks = [chunk async for chunk in pipeline.run(silent_stream(2), session)]

    assert chunks
    assert b"Are you still there" in chunks[0]
    assert session.transcript[-1]["event"] == "silence_prompt"
