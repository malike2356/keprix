"""Standalone FastAPI sidecar for the Clinicom HTTP contract.

Run:
    cd /opt/lampp/htdocs/verlox/keprix/domain-packs/clinicom
    uvicorn http_app:app --host 0.0.0.0 --port 3353
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

import tools.register  # noqa: F401  (registers handlers)
from tools.registry import registry

APP_NAME = os.getenv("CLINICOM_KEPRIX_SIDECAR_NAME", "Keprix Clinicom Sidecar")
SHARED_TOKEN = os.getenv("CLINICOM_SHARED_TOKEN", os.getenv("CLINICOM_SIDECAR_TOKEN", ""))

app = FastAPI(title=APP_NAME, version="0.1.0")


class TranscribeIn(BaseModel):
    audio: str
    mime_type: str = "audio/webm"
    language_hint: str | None = None
    context: str = "general-practice"


class TranslateIn(BaseModel):
    text: str
    source_language: str
    target_language: str
    context: str = "general-practice"


class SimplifyIn(BaseModel):
    text: str
    direction: str = "to-plain"
    target_reading_level: int = Field(default=8, ge=3, le=12)
    context: str = "general-practice"


class SpeakIn(BaseModel):
    text: str
    language: str
    voice: str = "auto"
    speed: float = 0.9


class CapabilitiesToolOut(BaseModel):
    name: str
    status: str
    latency_class: str
    requires_auth: bool
    source: str


class CapabilitiesOut(BaseModel):
    contract_version: str
    profile: str
    tools: list[CapabilitiesToolOut]
    provider_sources: dict[str, Any]
    loaded_at: str


class CulturalAdaptIn(BaseModel):
    text: str
    source_language: str = "en"
    target_language: str = "en"
    context: str = "general-practice"
    session_context: dict[str, Any] = Field(default_factory=dict)


class TeachbackScoreIn(BaseModel):
    patient_response: str
    key_points: list[str] = Field(default_factory=list)
    context: str = "general-practice"
    session_context: dict[str, Any] = Field(default_factory=dict)


class SafetyTriageAssistIn(BaseModel):
    text: str
    safety_terms: list[str] = Field(default_factory=list)
    context: str = "general-practice"
    session_context: dict[str, Any] = Field(default_factory=dict)


class SessionDigestIn(BaseModel):
    context: dict[str, Any] = Field(default_factory=dict)
    session_context: dict[str, Any] = Field(default_factory=dict)


class SpecialtySimplifyIn(BaseModel):
    text: str
    specialty_pack_id: str = "general"
    target_reading_level: int = Field(default=8, ge=3, le=12)
    context: str = "general-practice"
    session_context: dict[str, Any] = Field(default_factory=dict)


class ConfidenceExplainIn(BaseModel):
    score: int = 0
    provider_sources: dict[str, str] = Field(default_factory=dict)
    pipeline_timing: dict[str, float] = Field(default_factory=dict)
    step_status: list[dict[str, Any]] = Field(default_factory=list)
    context: str = "general-practice"


class ProductHelpIn(BaseModel):
    question: str
    grounding_corpus: str = ""
    capabilities_summary: str = ""


for _model in (
    TranscribeIn,
    TranslateIn,
    SimplifyIn,
    SpeakIn,
    CapabilitiesToolOut,
    CapabilitiesOut,
    CulturalAdaptIn,
    TeachbackScoreIn,
    SafetyTriageAssistIn,
    SessionDigestIn,
    SpecialtySimplifyIn,
    ConfidenceExplainIn,
    ProductHelpIn,
):
    _model.model_rebuild()


def _check_token(authorization: str | None) -> None:
    if not SHARED_TOKEN:
        return
    expected = f"Bearer {SHARED_TOKEN}"
    if authorization != expected:
        raise HTTPException(status_code=401, detail="Invalid sidecar token")


def _dispatch(tool: str, payload: dict[str, Any]) -> dict[str, Any]:
    raw = registry.dispatch(tool, payload)
    data = json.loads(raw)
    if data.get("status") == "error" or data.get("error"):
        raise HTTPException(status_code=400, detail=data.get("error") or "Tool dispatch failed")
    return data


@app.get("/clinicom/capabilities", response_model=CapabilitiesOut)
async def capabilities() -> dict[str, Any]:
    tools = [
        {"name": "transcribe", "status": "live", "latency_class": "high", "requires_auth": False, "source": "keprix"},
        {"name": "translate", "status": "live", "latency_class": "high", "requires_auth": False, "source": "keprix"},
        {"name": "simplify", "status": "live", "latency_class": "high", "requires_auth": False, "source": "keprix"},
        {"name": "speak", "status": "live", "latency_class": "high", "requires_auth": False, "source": "keprix"},
        {"name": "clinicom_cultural_adapt", "status": "stub", "latency_class": "medium", "requires_auth": False, "source": "keprix-clinicom-stub"},
        {"name": "clinicom_teachback_score", "status": "stub", "latency_class": "medium", "requires_auth": False, "source": "keprix-clinicom-stub"},
        {"name": "clinicom_safety_triage_assist", "status": "stub", "latency_class": "medium", "requires_auth": False, "source": "keprix-clinicom-stub"},
        {"name": "clinicom_session_digest", "status": "stub", "latency_class": "low", "requires_auth": False, "source": "keprix-clinicom-stub"},
        {"name": "clinicom_specialty_simplify", "status": "stub", "latency_class": "medium", "requires_auth": False, "source": "keprix-clinicom-stub"},
        {"name": "clinicom_confidence_explain", "status": "stub", "latency_class": "low", "requires_auth": False, "source": "keprix-clinicom-stub"},
        {"name": "product_help", "status": "live", "latency_class": "low", "requires_auth": False, "source": "keprix"},
    ]
    return {
        "contract_version": "2.0",
        "profile": "keprix",
        "tools": tools,
        "provider_sources": {
            "transcribe": "keprix",
            "translate": "keprix",
            "simplify": "keprix",
            "speak": "keprix",
            "product_help": "keprix",
        },
        "loaded_at": datetime.utcnow().isoformat(),
    }


@app.get("/health")
async def health() -> dict[str, str]:
    return {
        "status": "ok",
        "sidecar": "keprix-clinicom",
        "pack": "clinicom",
    }


@app.post("/clinicom/tools/transcribe")
async def transcribe(payload: TranscribeIn, authorization: str | None = Header(default=None)) -> dict[str, object]:
    _check_token(authorization)
    return _dispatch("clinicom_transcribe", payload.model_dump())


@app.post("/clinicom/tools/translate")
async def translate(payload: TranslateIn, authorization: str | None = Header(default=None)) -> dict[str, object]:
    _check_token(authorization)
    return _dispatch("clinicom_translate", payload.model_dump())


@app.post("/clinicom/tools/simplify")
async def simplify(payload: SimplifyIn, authorization: str | None = Header(default=None)) -> dict[str, object]:
    _check_token(authorization)
    return _dispatch("clinicom_simplify", payload.model_dump())


@app.post("/clinicom/tools/speak")
async def speak(payload: SpeakIn, authorization: str | None = Header(default=None)) -> dict[str, object]:
    _check_token(authorization)
    return _dispatch("clinicom_speak", payload.model_dump())


@app.post("/clinicom/tools/cultural_adapt")
async def cultural_adapt(payload: CulturalAdaptIn, authorization: str | None = Header(default=None)) -> dict[str, object]:
    _check_token(authorization)
    return _dispatch("clinicom_cultural_adapt", payload.model_dump())


@app.post("/clinicom/tools/teachback_score")
async def teachback_score(payload: TeachbackScoreIn, authorization: str | None = Header(default=None)) -> dict[str, object]:
    _check_token(authorization)
    return _dispatch("clinicom_teachback_score", payload.model_dump())


@app.post("/clinicom/tools/safety_triage_assist")
async def safety_triage_assist(payload: SafetyTriageAssistIn, authorization: str | None = Header(default=None)) -> dict[str, object]:
    _check_token(authorization)
    return _dispatch("clinicom_safety_triage_assist", payload.model_dump())


@app.post("/clinicom/tools/session_digest")
async def session_digest(payload: SessionDigestIn, authorization: str | None = Header(default=None)) -> dict[str, object]:
    _check_token(authorization)
    return _dispatch("clinicom_session_digest", payload.model_dump())


@app.post("/clinicom/tools/specialty_simplify")
async def specialty_simplify(payload: SpecialtySimplifyIn, authorization: str | None = Header(default=None)) -> dict[str, object]:
    _check_token(authorization)
    return _dispatch("clinicom_specialty_simplify", payload.model_dump())


@app.post("/clinicom/tools/confidence_explain")
async def confidence_explain(payload: ConfidenceExplainIn, authorization: str | None = Header(default=None)) -> dict[str, object]:
    _check_token(authorization)
    return _dispatch("clinicom_confidence_explain", payload.model_dump())


@app.post("/clinicom/tools/product_help")
async def product_help(payload: ProductHelpIn, authorization: str | None = Header(default=None)) -> dict[str, object]:
    _check_token(authorization)
    return _dispatch("clinicom_product_help", payload.model_dump())
