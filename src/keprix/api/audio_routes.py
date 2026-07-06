"""Workspace audio routes (STT) on the main FastAPI app."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from keprix.api.audio_transcribe import AudioTranscriptionRequest, transcribe_audio_upload
from keprix.api.stt_config import max_recording_seconds, stt_enabled, stt_provider
from keprix.auth.dependencies import get_current_user

router = APIRouter(prefix="/api/audio", tags=["audio"])


@router.get("/status")
async def audio_status() -> dict[str, Any]:
    """Return STT availability for workspace voice input UI."""
    return {
        "stt_enabled": stt_enabled(),
        "provider": stt_provider(),
        "max_recording_seconds": max_recording_seconds(),
        "transcribe_path": "/api/audio/transcribe",
    }


@router.post("/transcribe")
async def transcribe_authenticated(
    payload: AudioTranscriptionRequest,
    _user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    """Transcribe a browser-recorded audio clip for chat dictation."""
    return await transcribe_audio_upload(payload)
