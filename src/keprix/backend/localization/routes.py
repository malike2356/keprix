"""HTTP routes for localization."""

from __future__ import annotations

from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from keprix.auth.dependencies import get_current_user
from keprix.backend.localization.audit import get_audit_service
from keprix.backend.localization.catalog import catalog_as_dicts
from keprix.backend.localization.config import LocalizationSettings
from keprix.backend.localization.detection import detect_language
from keprix.backend.localization.glossary import get_glossary_service
from keprix.backend.localization.languages import build_language_catalog, config_from_env
from keprix.backend.localization.preferences import get_preference_service
from keprix.backend.localization.providers.nllb_200 import NLLB200Provider
from keprix.backend.localization.providers.seamless_m4t import SeamlessM4TProvider
from keprix.backend.localization.router import LocalizationConfig, ProviderConfig
from keprix.backend.localization.schemas import TranslationRequest
from keprix.backend.localization.speech import synthesize_speech
from keprix.backend.localization.transcription import transcribe_audio
from keprix.backend.localization.translation import TranslationService

router = APIRouter(prefix="/api/localization", tags=["localization"])


def _user_id(user: dict[str, Any]) -> str:
    return str(user.get("id") or user.get("username") or "default")


def _runtime_config(
    *,
    sm4t_enabled: bool | None = None,
    nllb_enabled: bool | None = None,
) -> LocalizationConfig:
    config = config_from_env()
    if sm4t_enabled is not None:
        config.seamless_m4t = ProviderConfig(
            enabled=sm4t_enabled,
            sidecar_url=config.seamless_m4t.sidecar_url,
        )
    if nllb_enabled is not None:
        config.nllb_200 = ProviderConfig(
            enabled=nllb_enabled,
            sidecar_url=config.nllb_200.sidecar_url,
        )
    return config


class DetectBody(BaseModel):
    text: str = Field(..., min_length=1)
    hint: str | None = None


class TranslateBody(BaseModel):
    text: str = Field(..., min_length=1)
    source_language: str | None = None
    target_language: str
    workspace_id: str = "default"
    glossary_id: str | None = None
    preserve_terms: list[str] = Field(default_factory=list)


class TranscribeBody(BaseModel):
    audio_base64: str
    source_language: str | None = None
    target_language: str = "en"


class SpeechBody(BaseModel):
    text: str = Field(..., min_length=1)
    language: str
    workspace_id: str = "default"


class PreferencesBody(BaseModel):
    preferred_input_language: str | None = None
    preferred_output_language: str | None = None
    voice_output_enabled: bool | None = None
    preferred_voice_id: str | None = None
    bilingual_replies: bool | None = None


class GlossaryBody(BaseModel):
    id: str | None = None
    domain: str
    entries: list[dict[str, Any]] = Field(default_factory=list)


@router.get("/languages")
async def list_languages(
    sm4t_enabled: bool | None = Query(default=None),
    nllb_enabled: bool | None = Query(default=None),
) -> dict[str, Any]:
    config = _runtime_config(sm4t_enabled=sm4t_enabled, nllb_enabled=nllb_enabled)
    return {
        "languages": build_language_catalog(config),
        "catalog": catalog_as_dicts(),
    }


@router.post("/detect")
async def detect(body: DetectBody, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    settings = LocalizationSettings.from_env()
    result = await detect_language(
        body.text,
        hint=body.hint,
        allow_cloud=settings.allowed_cloud_processing,
    )
    return {
        "language_code": result.language_code,
        "language_name": result.language_name,
        "confidence": result.confidence,
        "provider": result.provider,
        "script": result.script,
        "region": result.region,
        "alternatives": result.alternatives,
        "user_id": _user_id(user),
    }


@router.post("/translate")
async def translate(body: TranslateBody, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    service = TranslationService()
    result = await service.translate(
        TranslationRequest(
            workspace_id=body.workspace_id,
            text=body.text,
            source_language=body.source_language,
            target_language=body.target_language,
            glossary_id=body.glossary_id,
            preserve_terms=body.preserve_terms,
            user_id=_user_id(user),
        )
    )
    return {
        "source_language": result.source_language,
        "target_language": result.target_language,
        "source_text": result.source_text,
        "translated_text": result.translated_text,
        "confidence": result.confidence,
        "glossary_matches": result.glossary_matches,
        "warnings": result.warnings,
        "provider": result.provider,
    }


@router.post("/transcribe")
async def transcribe(body: TranscribeBody, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    import base64

    audio = base64.b64decode(body.audio_base64)
    result = await transcribe_audio(
        audio,
        source_language=body.source_language,
        target_language=body.target_language,
    )
    return {
        "language_code": result.language_code,
        "transcript": result.transcript,
        "confidence": result.confidence,
        "segments": [
            {"start": s.start, "end": s.end, "text": s.text, "confidence": s.confidence}
            for s in result.segments
        ],
        "provider": result.provider,
        "user_id": _user_id(user),
    }


@router.post("/speech")
async def speech(body: SpeechBody, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    result = await synthesize_speech(
        body.text,
        body.language,
        workspace_id=body.workspace_id,
        user_id=_user_id(user),
    )
    if result is None:
        raise HTTPException(status_code=422, detail="Speech output unavailable for this user or channel")
    return {
        "language_code": result.language_code,
        "voice_id": result.voice_id,
        "audio_url": result.audio_url,
        "transcript": result.transcript,
        "provider": result.provider,
        "user_id": _user_id(user),
    }


@router.get("/preferences")
async def get_preferences(
    workspace_id: str = "default",
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    settings = LocalizationSettings.from_env(workspace_id)
    return await get_preference_service().get(workspace_id, _user_id(user), settings)


@router.post("/preferences")
async def update_preferences(
    body: PreferencesBody,
    workspace_id: str = "default",
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    patch = body.model_dump(exclude_none=True)
    return await get_preference_service().update(workspace_id, _user_id(user), patch)


@router.get("/glossaries")
async def list_glossaries(_user: dict = Depends(get_current_user)) -> dict[str, Any]:
    return {"glossaries": get_glossary_service().list_glossaries()}


@router.post("/glossaries")
async def save_glossary(body: GlossaryBody, _user: dict = Depends(get_current_user)) -> dict[str, Any]:
    saved = get_glossary_service().save(body.model_dump())
    return {"glossary": saved}


@router.get("/audit")
async def list_audit(
    workspace_id: str = "default",
    limit: int = Query(default=50, ge=1, le=200),
    human_review_required: bool | None = None,
    _user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    return {
        "records": await get_audit_service().list_records(
            workspace_id,
            limit=limit,
            human_review_required=human_review_required,
        )
    }


@router.get("/providers/health")
async def provider_health() -> dict[str, Any]:
    sm4t = SeamlessM4TProvider()
    nllb = NLLB200Provider()
    return {
        "seamless_m4t": await sm4t.health_check(),
        "nllb_200": await nllb.health_check(),
    }


@router.get("/providers/sm4t/health")
async def sm4t_sidecar_health() -> dict[str, Any]:
    config = config_from_env()
    url = config.seamless_m4t.sidecar_url.rstrip("/") + "/health"
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.get(url)
            return response.json()
    except Exception as exc:
        return {"status": "error", "detail": str(exc)}
