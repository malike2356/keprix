"""Twilio Media Stream audio helpers."""

from __future__ import annotations

import base64
import json

try:
    import audioop
except ImportError:  # pragma: no cover - Python 3.13 environments use audioop-lts.
    import audioop_lts as audioop  # type: ignore[no-redef]


def mulaw_to_pcm(data: bytes, *, input_rate: int = 8000, output_rate: int = 16000) -> bytes:
    pcm = audioop.ulaw2lin(data, 2)
    if input_rate == output_rate:
        return pcm
    converted, _state = audioop.ratecv(pcm, 2, 1, input_rate, output_rate, None)
    return converted


def pcm_to_mulaw(data: bytes, *, input_rate: int = 16000, output_rate: int = 8000) -> bytes:
    pcm = data
    if input_rate != output_rate:
        pcm, _state = audioop.ratecv(data, 2, 1, input_rate, output_rate, None)
    return audioop.lin2ulaw(pcm, 2)


def build_twilio_media_message(audio: bytes, *, stream_sid: str = "") -> str:
    return json.dumps(
        {
            "event": "media",
            "streamSid": stream_sid,
            "media": {"payload": base64.b64encode(audio).decode("ascii")},
        }
    )


def parse_twilio_media_payload(message: str) -> bytes | None:
    event = json.loads(message)
    if event.get("event") != "media":
        return None
    payload = (event.get("media") or {}).get("payload")
    if not payload:
        return None
    return base64.b64decode(payload)
