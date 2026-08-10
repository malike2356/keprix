"""HTTP API for AI transparency consent, generation log, and compliance reports."""

from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

from keprix.transparency.consent_gate import AI_FEATURES, ConsentRequiredError, get_consent_gate
from keprix.transparency.generation_log import get_generation_log_store
from keprix.transparency.labels import DISCLOSURE_TEXT, SgiLabeler
from keprix.transparency.pipeline import finalize_ai_output, prepare_ai_call

router = APIRouter(prefix="/api/transparency", tags=["transparency"])


def _user_id(request: Request) -> str:
    header = request.headers.get("x-user-id", "").strip()
    return header or "local"


class ConsentBody(BaseModel):
    feature: str = Field(..., min_length=1)
    action: Literal["granted", "denied", "withdrawn"] = "granted"
    affirmative: bool = True


class LabelBody(BaseModel):
    output: str
    content_type: Literal["text", "image", "code", "audio", "video"] = "text"
    locale: str = "en"
    model_name: str | None = None


class FinalizeBody(BaseModel):
    input_payload: str
    output_payload: str
    model_name: str
    content_type: Literal["text", "image", "code", "audio", "video"] = "text"
    feature_endpoint: str = "chat"
    feature: str = "text_generation"
    session_id: str | None = None
    locale: str = "en"


@router.get("/features")
async def list_features() -> dict[str, Any]:
    return {"features": list(AI_FEATURES)}


@router.get("/disclosure")
async def disclosure(locale: str = Query(default="en")) -> dict[str, Any]:
    labeler = SgiLabeler()
    return {
        "locale": locale,
        "text": labeler.get_disclosure_text(locale),
        "removable": labeler.is_label_removable(),
        "locales": sorted(DISCLOSURE_TEXT.keys()),
    }


@router.post("/label")
async def label_output(body: LabelBody) -> dict[str, Any]:
    result = SgiLabeler().label_output(
        body.output,
        body.content_type,
        locale=body.locale,
        model_name=body.model_name,
    )
    return result


@router.get("/consent")
async def consent_status(request: Request) -> dict[str, Any]:
    return get_consent_gate().get_consent_status(_user_id(request))


@router.post("/consent")
async def record_consent(body: ConsentBody, request: Request) -> dict[str, Any]:
    try:
        row = get_consent_gate().record_consent(
            _user_id(request),
            body.feature,
            action=body.action,
            affirmative=body.affirmative,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"consent": row}


@router.post("/consent/check")
async def check_consent(body: ConsentBody, request: Request) -> dict[str, Any]:
    try:
        return prepare_ai_call(_user_id(request), body.feature)
    except ConsentRequiredError as exc:
        raise HTTPException(
            status_code=403,
            detail={"code": "ai_consent_required", "feature": exc.feature, "message": str(exc)},
        ) from exc


@router.get("/generation-log")
async def query_generation_log(
    start: str | None = None,
    end: str | None = None,
    user_id: str | None = None,
    model_name: str | None = None,
    feature_endpoint: str | None = None,
    limit: int = Query(default=200, ge=1, le=5000),
) -> dict[str, Any]:
    rows = get_generation_log_store().query_log(
        start=start,
        end=end,
        user_id=user_id,
        model_name=model_name,
        feature_endpoint=feature_endpoint,
        limit=limit,
    )
    return {"entries": rows, "count": len(rows)}


@router.get("/compliance-report")
async def compliance_report(date: str = Query(..., min_length=10, max_length=32)) -> dict[str, Any]:
    return get_generation_log_store().generate_compliance_report(date)


@router.post("/finalize")
async def finalize(body: FinalizeBody, request: Request) -> dict[str, Any]:
    try:
        result = finalize_ai_output(
            input_payload=body.input_payload,
            output_payload=body.output_payload,
            model_name=body.model_name,
            user_id=_user_id(request),
            content_type=body.content_type,
            feature_endpoint=body.feature_endpoint,
            feature=body.feature,
            session_id=body.session_id,
            locale=body.locale,
        )
    except ConsentRequiredError as exc:
        raise HTTPException(
            status_code=403,
            detail={"code": "ai_consent_required", "feature": exc.feature, "message": str(exc)},
        ) from exc
    return result
