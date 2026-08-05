"""Analytics workspace REST endpoints (Prompt 54)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel

from keprix.analytics.code_interpreter import AnalyticsSession, CodeInterpreter
from keprix.analytics.container_executor import ContainerExecutor
from keprix.analytics.file_import import (
    AnalyticsImportError,
    parse_analytics_file,
    supported_analytics_formats,
)
from keprix.analytics.reflective_execution import ReflectiveExecutor
from keprix.api.auth import require_api_auth

router = APIRouter(prefix="/api/analytics", tags=["analytics-workspace"])

_executor = ContainerExecutor(container_required=False)
_interpreter = CodeInterpreter(executor=_executor)
_reflective = ReflectiveExecutor(_interpreter)


def get_workspace_interpreter() -> CodeInterpreter:
    return _interpreter


class RunRequest(BaseModel):
    code: str
    auto_repair: bool = True


class ApproveRequest(BaseModel):
    approve_network: bool = False
    approve_shell: bool = False


class CreateSessionBody(BaseModel):
    title: str | None = None


class RenameSessionBody(BaseModel):
    title: str


class DatasetBody(BaseModel):
    name: str
    data: str
    source_filename: str | None = None


def _get_session(session_id: str) -> AnalyticsSession:
    session = _interpreter.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.post("/sessions")
async def create_session(body: CreateSessionBody | None = None, _user: str = Depends(require_api_auth)) -> dict:
    session = _interpreter.create_session(title=(body.title if body else None))
    return session.to_dict()


@router.patch("/sessions/{session_id}")
async def rename_session(
    session_id: str,
    body: RenameSessionBody,
    _user: str = Depends(require_api_auth),
) -> dict:
    session = _interpreter.rename_session(session_id, body.title)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return session.to_dict()


@router.get("/sessions")
async def list_sessions(_user: str = Depends(require_api_auth)) -> dict:
    sessions = sorted(
        _interpreter.sessions.values(),
        key=lambda item: item.created_at,
        reverse=True,
    )
    return {
        "sessions": [
            {
                **session.to_dict(),
                "code_runs": len(session.code_history),
            }
            for session in sessions
        ],
    }


@router.get("/datasets")
async def list_datasets(_user: str = Depends(require_api_auth)) -> dict:
    return {
        "datasets": [
            {
                "dataset_id": item["dataset_id"],
                "name": item["name"],
                "source_filename": item.get("source_filename"),
                "created_at": item["created_at"],
                "chars": len(item.get("data") or ""),
            }
            for item in _interpreter.list_datasets()
        ]
    }


@router.post("/datasets")
async def save_dataset(body: DatasetBody, _user: str = Depends(require_api_auth)) -> dict:
    if not body.data.strip():
        raise HTTPException(status_code=400, detail="Dataset data is empty")
    return _interpreter.save_dataset(
        name=body.name,
        data=body.data,
        source_filename=body.source_filename,
    )


@router.get("/datasets/{dataset_id}")
async def get_dataset(dataset_id: str, _user: str = Depends(require_api_auth)) -> dict:
    item = _interpreter.get_dataset(dataset_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return item


@router.delete("/datasets/{dataset_id}")
async def delete_dataset(dataset_id: str, _user: str = Depends(require_api_auth)) -> dict:
    ok = _interpreter.delete_dataset(dataset_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return {"ok": True}


@router.get("/supported-formats")
async def list_supported_formats(_user: str = Depends(require_api_auth)) -> dict:
    return {"formats": supported_analytics_formats()}


@router.post("/parse-file")
async def parse_file_upload(
    file: UploadFile = File(...),
    _user: str = Depends(require_api_auth),
) -> dict:
    raw = await file.read()
    filename = file.filename or "upload.csv"
    try:
        return parse_analytics_file(filename, raw)
    except AnalyticsImportError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/sessions/{session_id}/run")
async def run_code(
    session_id: str,
    body: RunRequest,
    _user: str = Depends(require_api_auth),
) -> dict:
    session = _get_session(session_id)
    if body.auto_repair:
        ok, trail = _reflective.run_with_repair(session, body.code)
        last = trail.attempts[-1] if trail.attempts else {}
        return {
            "ok": ok,
            "stdout": last.get("stdout") or "",
            "stderr": last.get("error") or "",
            "trail": [dict(a) for a in trail.attempts],
        }
    verification, result = _interpreter.run_code(session, body.code)
    return {
        "ok": result.ok,
        "verification_passed": verification.allowed,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


@router.get("/sessions/{session_id}")
async def get_session(session_id: str, _user: str = Depends(require_api_auth)) -> dict:
    return _get_session(session_id).to_dict()


@router.get("/sessions/{session_id}/artifacts")
async def get_artifacts(session_id: str, _user: str = Depends(require_api_auth)) -> dict:
    session = _get_session(session_id)
    return {"artifacts": list(session.artifacts), "charts": list(session.charts)}


@router.post("/sessions/{session_id}/approve")
async def approve_session(
    session_id: str,
    body: ApproveRequest,
    _user: str = Depends(require_api_auth),
) -> dict:
    session = _get_session(session_id)
    session.approved_network = body.approve_network
    session.approved_shell = body.approve_shell
    return {
        "session_id": session_id,
        "approved_network": session.approved_network,
        "approved_shell": session.approved_shell,
    }
