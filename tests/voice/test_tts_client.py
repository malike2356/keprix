import pytest

from keprix.voice.tts_client import TTSStreamingClient


@pytest.mark.asyncio
async def test_tts_streaming_facade_yields_voice_audio() -> None:
    client = TTSStreamingClient()
    chunks = [chunk async for chunk in client.stream("hello. welcome", voice_id="rachel")]

    assert chunks
    assert chunks[0].startswith(b"audio:rachel:")


def test_tts_stream_can_be_interrupted() -> None:
    client = TTSStreamingClient()
    client.interrupt()

    assert client.interrupted
