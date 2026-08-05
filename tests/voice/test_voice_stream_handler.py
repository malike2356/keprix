import base64

from fastapi.testclient import TestClient

from keprix.api.server import create_app
from keprix.voice.call_store import VoiceCallStore, reset_call_store


def test_voice_stream_handler_finalises_call_record() -> None:
    reset_call_store()
    client = TestClient(create_app())
    import anyio

    async def create_record() -> None:
        await VoiceCallStore().create("CA123", worker_id="worker-1", caller="+155501")

    anyio.run(create_record)

    with client.websocket_connect("/api/voice/stream/CA123") as websocket:
        websocket.send_json(
            {
                "event": "media",
                "streamSid": "MZ123",
                "media": {"payload": base64.b64encode(b"\xff" * 80).decode("ascii")},
            }
        )
        websocket.send_json({"event": "stop", "streamSid": "MZ123"})

    async def load_record():
        return await VoiceCallStore().get("CA123")

    record = anyio.run(load_record)
    assert record is not None
    assert record.ended_at is not None
    assert record.summary is not None
