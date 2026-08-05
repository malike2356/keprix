import base64
import json

from keprix.gateway.voice_audio import build_twilio_media_message, mulaw_to_pcm, parse_twilio_media_payload, pcm_to_mulaw


def test_twilio_media_envelope_round_trip() -> None:
    audio = b"\xff" * 80
    message = build_twilio_media_message(audio, stream_sid="MZ123")
    payload = json.loads(message)

    assert payload["streamSid"] == "MZ123"
    assert base64.b64decode(payload["media"]["payload"]) == audio
    assert parse_twilio_media_payload(message) == audio


def test_mulaw_pcm_conversion_produces_audio_bytes() -> None:
    pcm = mulaw_to_pcm(b"\xff" * 80)
    mulaw = pcm_to_mulaw(pcm)

    assert pcm
    assert mulaw
