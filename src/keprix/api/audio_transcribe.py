"""Shared audio transcription handler for workspace API and Keprix desktop."""

from __future__ import annotations

import asyncio
import base64
import binascii
import logging
import os
import tempfile
from typing import Any

from fastapi import HTTPException
from pydantic import BaseModel

from keprix.api.audio_limits import MAX_TRANSCRIPTION_UPLOAD_BYTES, audio_extension_for_mime
from keprix.api.stt_config import stt_enabled

_log = logging.getLogger(__name__)


class AudioTranscriptionRequest(BaseModel):
    data_url: str
    mime_type: str | None = None


async def transcribe_audio_upload(
    payload: AudioTranscriptionRequest,
    *,
    check_stt_enabled: bool = True,
) -> dict[str, Any]:
    """Decode a base64 data URL, transcribe audio, and return the transcription contract."""
    if check_stt_enabled and not stt_enabled():
        raise HTTPException(status_code=403, detail="Speech-to-text is disabled")

    data_url = (payload.data_url or "").strip()
    if not data_url.startswith("data:") or "," not in data_url:
        raise HTTPException(status_code=400, detail="Invalid audio payload")

    header, encoded = data_url.split(",", 1)
    if ";base64" not in header:
        raise HTTPException(status_code=400, detail="Audio payload must be base64 encoded")

    mime_type = (
        payload.mime_type or header[5:].split(";", 1)[0] or "audio/webm"
    ).strip()
    normalized_mime_type = mime_type.split(";", 1)[0].lower()
    if not (
        normalized_mime_type.startswith("audio/")
        or normalized_mime_type == "video/webm"
    ):
        raise HTTPException(status_code=400, detail="Payload must be an audio recording")

    try:
        audio_bytes = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError):
        raise HTTPException(status_code=400, detail="Audio payload is not valid base64")

    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Audio recording is empty")
    if len(audio_bytes) > MAX_TRANSCRIPTION_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Audio recording is too large")

    temp_path = ""
    try:
        suffix = audio_extension_for_mime(mime_type)
        with tempfile.NamedTemporaryFile(
            prefix="keprix-voice-",
            suffix=suffix,
            delete=False,
        ) as tmp:
            tmp.write(audio_bytes)
            temp_path = tmp.name

        from tools.transcription_tools import transcribe_audio

        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(None, transcribe_audio, temp_path)
    except HTTPException:
        raise
    except Exception as exc:
        _log.exception("Voice transcription failed")
        raise HTTPException(status_code=500, detail=f"Transcription failed: {exc}") from exc
    finally:
        if temp_path:
            try:
                os.unlink(temp_path)
            except OSError:
                pass

    if not result.get("success"):
        raise HTTPException(
            status_code=400,
            detail=result.get("error") or "Transcription failed",
        )

    return {
        "ok": True,
        "transcript": str(result.get("transcript") or "").strip(),
        "provider": result.get("provider"),
    }
