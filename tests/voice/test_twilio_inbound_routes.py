import base64
import hashlib
import hmac

from fastapi.testclient import TestClient

from keprix.api.server import create_app
from keprix.gateway.twilio_voice_webhook import validate_twilio_signature
from keprix.voice.call_store import VoiceCallStore, reset_call_store


def _signature(url: str, params: dict[str, str], token: str) -> str:
    payload = url + "".join(f"{key}{params[key]}" for key in sorted(params))
    digest = hmac.new(token.encode("utf-8"), payload.encode("utf-8"), hashlib.sha1).digest()
    return base64.b64encode(digest).decode("ascii")


def test_validate_twilio_signature() -> None:
    params = {"CallSid": "CA123", "From": "+155501", "To": "+155502"}
    sig = _signature("https://voice.example.test/api/voice/inbound", params, "secret")

    assert validate_twilio_signature("https://voice.example.test/api/voice/inbound", params, sig, "secret")
    assert not validate_twilio_signature("https://voice.example.test/api/voice/inbound", params, "bad", "secret")


def test_inbound_voice_rejects_bad_signature(monkeypatch) -> None:
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", "secret")
    reset_call_store()
    client = TestClient(create_app())

    response = client.post("/api/voice/inbound", data={"CallSid": "CA123", "From": "+155501", "To": "+155502"})

    assert response.status_code == 403
    assert "<Reject" in response.text


def test_inbound_voice_accepts_signed_request(monkeypatch) -> None:
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", "secret")
    reset_call_store()
    client = TestClient(create_app())
    params = {"CallSid": "CA123", "From": "+155501", "To": "+155502"}
    sig = _signature("http://testserver/api/voice/inbound", params, "secret")

    response = client.post("/api/voice/inbound", data=params, headers={"X-Twilio-Signature": sig})

    assert response.status_code == 200
    assert "/api/voice/stream/CA123" in response.text

    import anyio

    async def load_record():
        return await VoiceCallStore().get("CA123")

    assert anyio.run(load_record) is not None
