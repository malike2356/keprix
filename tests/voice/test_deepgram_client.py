import pytest

from keprix.voice.deepgram_client import DeepgramStreamingClient


@pytest.mark.asyncio
async def test_deepgram_streaming_facade_returns_transcript() -> None:
    async with DeepgramStreamingClient().session() as session:
        await session.send(b"hello ")
        await session.send(b"there")
        transcript = await session.finish()

    assert transcript == "hello there"
