"""Phase 5 polish APIs: token playbook, guardrails, error-paste helpers."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from keprix.agent_os.guardrails import backup_vault, guardrails_status
from keprix.agent_os.token_playbook import playbook_status
from keprix.agent_os.workflow_audit_service import agent_os_enabled
from keprix.agent_os.workflows.error_paste import analyze_error_paste
from keprix.auth.dependencies import get_current_user

router = APIRouter(prefix="/api/agent-os", tags=["agent-os"])


class ErrorPasteBody(BaseModel):
    error_text: str = Field(..., min_length=1)
    context: str = ""


def _guard() -> None:
    if not agent_os_enabled():
        raise HTTPException(status_code=403, detail="Agent OS is disabled")


@router.get("/token-playbook")
async def get_token_playbook(user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _ = user
    _guard()
    return playbook_status()


@router.get("/guardrails")
async def get_guardrails(user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _ = user
    _guard()
    return guardrails_status()


@router.post("/guardrails/backup-vault")
async def post_vault_backup(user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _ = user
    _guard()
    return backup_vault(reason="manual")


@router.post("/error-paste")
async def post_error_paste(body: ErrorPasteBody, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _ = user
    _guard()
    return analyze_error_paste(error_text=body.error_text, context=body.context)
