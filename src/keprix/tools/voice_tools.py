"""Tools for inspecting and controlling Aiva phone calls."""

from __future__ import annotations

from keprix.voice.call_store import VoiceCallStore
from keprix.voice.twiml_builder import dial_transfer_response


async def get_call_transcript(call_sid: str) -> dict:
    record = await VoiceCallStore().get(call_sid)
    if record is None:
        return {"ok": False, "error": "call not found"}
    return {"ok": True, "call_sid": call_sid, "transcript": [turn.to_dict() for turn in record.transcript]}


def transfer_call(call_sid: str, phone_number: str) -> dict:
    return {
        "ok": True,
        "call_sid": call_sid,
        "twiml": dial_transfer_response(phone_number, "Let me transfer you now."),
    }


def send_voicemail(call_sid: str, message: str) -> dict:
    return {"ok": True, "call_sid": call_sid, "message": message, "action": "voicemail"}
