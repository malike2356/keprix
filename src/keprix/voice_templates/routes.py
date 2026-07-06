"""Voice template HTTP routes (Prompt 49)."""

from __future__ import annotations

from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, Response
from starlette.requests import Request

from keprix.auth.dependencies import get_current_user, require_admin
from keprix.voice_templates.approval import (
    approve_template,
    reject_template,
    submit_template,
    validate_upload_content_type,
)
from keprix.voice_templates.audio_utils import AudioFormatError
from keprix.voice_templates.library import get_template_library
from keprix.voice_templates.player import get_voice_player
from keprix.voice_templates.schemas import (
    ApproveBody,
    AssembleBody,
    CategoryCreate,
    LanguageFallbackUpdate,
    RejectBody,
    VoiceResponseAssemblyOut,
)
from keprix.voice_templates.store import get_voice_template_store

router = APIRouter(prefix="/api/voice-templates", tags=["voice-templates"])


def _workspace_id(request: Request, explicit: str | None = None) -> str:
    if explicit:
        return explicit.strip()
    header = request.headers.get("x-workspace-id", "").strip()
    return header or "default"


def _template_out(record, *, request: Request | None = None) -> dict[str, Any]:
    audio_url = f"/api/voice-templates/{record.id}/audio"
    return record.to_dict(audio_url=audio_url)


@router.get("/categories")
async def list_categories(domain: str | None = None) -> list[dict[str, Any]]:
    return get_template_library().list_categories(domain=domain)


@router.post("/categories/register")
async def register_category(
    body: CategoryCreate,
    _admin: dict = Depends(require_admin),
) -> dict[str, Any]:
    return get_template_library().register_category(body)


@router.get("/coverage")
async def coverage_report() -> dict[str, Any]:
    report = await get_template_library().get_languages_with_coverage()
    return {"languages": report}


@router.get("")
async def list_templates(
    request: Request,
    language_code: str | None = None,
    category_id: str | None = None,
    status: str | None = None,
    workspace_id: str | None = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> list[dict[str, Any]]:
    store = get_voice_template_store()
    ws = workspace_id if workspace_id is not None else None
    rows = store.list_templates(
        language_code=language_code,
        category_id=category_id,
        status=status,  # type: ignore[arg-type]
        workspace_id=ws,
        limit=limit,
        offset=offset,
    )
    return [_template_out(r, request=request) for r in rows]


@router.post("/assemble", response_model=VoiceResponseAssemblyOut)
async def assemble_response(body: AssembleBody) -> dict[str, Any]:
    player = get_voice_player()
    workspace = body.workspace_id or "default"
    result = await player.assemble_response(
        category_id=body.category_id,
        language_code=body.language_code,
        dynamic_text=body.dynamic_text,
        full_text_fallback=body.full_text_fallback,
        workspace_id=workspace,
    )
    return {
        "audio_url": result.audio_url,
        "transcript": result.transcript,
        "method": result.method,
        "template_id": result.template_id,
    }


@router.put("/fallbacks")
async def set_language_fallback(
    body: LanguageFallbackUpdate,
    _admin: dict = Depends(require_admin),
) -> dict[str, str]:
    store = get_voice_template_store()
    store.set_language_fallback(body.language_code, body.fallback_language_code)
    return store.language_fallbacks


@router.get("/fallbacks")
async def get_language_fallbacks() -> dict[str, str]:
    return get_voice_template_store().language_fallbacks


@router.get("/temp/{token}/audio")
async def get_temp_audio(token: str) -> FileResponse:
    path = get_voice_template_store().get_temp_path(token)
    if path is None:
        raise HTTPException(404, "Assembled audio not found")
    return FileResponse(path, media_type="audio/wav", filename=f"{token}.wav")


@router.post("", status_code=201)
async def upload_template(
    request: Request,
    audio_file: UploadFile = File(...),
    category_id: str = Form(...),
    language_code: str = Form(...),
    transcript: str = Form(...),
    transcript_english: str = Form(...),
    recorded_by: str = Form(...),
    recorded_at: date = Form(...),
    dialect_note: str | None = Form(None),
    workspace_id: str | None = Form(None),
    _user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    try:
        validate_upload_content_type(audio_file.content_type, audio_file.filename)
    except AudioFormatError as exc:
        raise HTTPException(422, str(exc)) from exc
    content = await audio_file.read()
    try:
        record = await submit_template(
            workspace_id=_workspace_id(request, workspace_id),
            category_id=category_id,
            language_code=language_code,
            audio_bytes=content,
            transcript=transcript,
            transcript_english=transcript_english,
            recorded_by=recorded_by,
            recorded_at=recorded_at,
            dialect_note=dialect_note,
        )
    except AudioFormatError as exc:
        raise HTTPException(422, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return {"template_id": record.id, "status": record.status}


@router.get("/{template_id}")
async def get_template(template_id: str, request: Request) -> dict[str, Any]:
    record = get_voice_template_store().get_template(template_id)
    if record is None:
        raise HTTPException(404, "Template not found")
    return _template_out(record, request=request)


@router.get("/{template_id}/audio")
async def get_template_audio(template_id: str) -> Response:
    store = get_voice_template_store()
    record = store.get_template(template_id)
    if record is None:
        raise HTTPException(404, "Template not found")
    data = store.get_audio_bytes(record.audio_file_id, record.workspace_id)
    if data is None:
        raise HTTPException(404, "Audio file not found")
    return Response(content=data, media_type="audio/wav")


@router.post("/{template_id}/approve")
async def approve_template_route(
    template_id: str,
    body: ApproveBody,
    user: dict = Depends(require_admin),
) -> dict[str, Any]:
    record = await approve_template(
        template_id,
        approver_user_id=str(user.get("id") or user.get("username") or "admin"),
        quality_rating=body.quality_rating,
    )
    if record is None:
        raise HTTPException(404, "Template not found")
    return _template_out(record)


@router.post("/{template_id}/reject")
async def reject_template_route(
    template_id: str,
    body: RejectBody,
    _admin: dict = Depends(require_admin),
) -> dict[str, Any]:
    record = await reject_template(template_id, reason=body.reason)
    if record is None:
        raise HTTPException(404, "Template not found")
    return _template_out(record)


@router.delete("/{template_id}")
async def archive_template_route(
    template_id: str,
    _admin: dict = Depends(require_admin),
) -> dict[str, bool]:
    record = get_voice_template_store().archive_template(template_id)
    if record is None:
        raise HTTPException(404, "Template not found")
    return {"archived": True}
