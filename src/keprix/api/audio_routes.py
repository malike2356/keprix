"""Workspace audio routes (STT) on the main FastAPI app."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from keprix.api.audio_transcribe import AudioTranscriptionRequest, transcribe_audio_upload
from keprix.api.stt_config import max_recording_seconds, stt_enabled, stt_provider
from keprix.api.voice_settings import update_voice_settings, voice_settings_snapshot
from keprix.auth.dependencies import get_current_user

router = APIRouter(prefix="/api/audio", tags=["audio"])


class VoiceSettingsBody(BaseModel):
    enabled: bool | None = None
    provider: str | None = None
    max_recording_seconds: int | None = Field(default=None, alias="maxRecordingSeconds")
    local_model: str | None = Field(default=None, alias="localModel")
    local_language: str | None = Field(default=None, alias="localLanguage")
    openai_model: str | None = Field(default=None, alias="openaiModel")
    mistral_model: str | None = Field(default=None, alias="mistralModel")
    elevenlabs_model: str | None = Field(default=None, alias="elevenlabsModel")
    groq_model: str | None = Field(default=None, alias="groqModel")
    gemini_model: str | None = Field(default=None, alias="geminiModel")
    auto_tts: bool | None = Field(default=None, alias="autoTts")
    beep_enabled: bool | None = Field(default=None, alias="beepEnabled")
    api_keys: dict[str, str | None] | None = Field(default=None, alias="apiKeys")
    clear_api_key_for: str | None = Field(default=None, alias="clearApiKeyFor")

    model_config = {"populate_by_name": True}


@router.get("/status")
async def audio_status() -> dict[str, Any]:
    """Return STT availability for workspace voice input UI."""
    return {
        "stt_enabled": stt_enabled(),
        "provider": stt_provider(),
        "max_recording_seconds": max_recording_seconds(),
        "transcribe_path": "/api/audio/transcribe",
    }


@router.get("/settings")
async def audio_settings(_user: dict = Depends(get_current_user)) -> dict[str, Any]:
    """Full editable snapshot for Settings -> Voice."""
    _ = _user
    return voice_settings_snapshot()


@router.put("/settings")
async def put_audio_settings(
    body: VoiceSettingsBody,
    _user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    """Persist STT/voice settings from the GUI (writes config.yaml + optional env keys)."""
    _ = _user
    try:
        return update_voice_settings(body.model_dump(by_alias=False, exclude_unset=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to save voice settings: {exc}") from exc


@router.post("/transcribe")
async def transcribe_authenticated(
    payload: AudioTranscriptionRequest,
    _user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    """Transcribe a browser-recorded audio clip for chat dictation."""
    return await transcribe_audio_upload(payload)
