"""HTTP routes for NL playbook drafting (Prompt 208)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from keprix.auth.dependencies import get_current_user
from keprix.playbook.nl_builder import PlaybookDraftRequest, PlaybookDraftResult, generate_playbook_yaml

router = APIRouter(prefix="/api/playbooks", tags=["playbooks"])


@router.post("/draft-from-prompt", response_model=PlaybookDraftResult)
async def draft_playbook_from_prompt(
    body: PlaybookDraftRequest,
    _user: dict = Depends(get_current_user),
) -> PlaybookDraftResult:
    try:
        return await generate_playbook_yaml(body)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail={"message": str(exc), "warnings": [str(exc)]}) from exc
