"""HTTP control-plane routes for the Textual TUI (steer, interrupt, config)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from keprix.api.turn_registry import (
    BUSY_INPUT_MODES,
    NotBusyError,
    get_busy_input_mode,
    turn_registry,
)
from keprix.auth.dependencies import get_current_user

router = APIRouter(tags=["tui"])


class SteerBody(BaseModel):
    text: str = Field(..., min_length=1)


class InterruptBody(BaseModel):
    keep_queue: bool = False


class ClarifyRespondBody(BaseModel):
    answer: str = ""
    text: str | None = None


class ApprovalRespondBody(BaseModel):
    decision: str = Field(..., min_length=1)


@router.get("/api/tui/config")
async def tui_config(_user: dict = Depends(get_current_user)) -> dict[str, object]:
    mode = get_busy_input_mode()
    details: dict[str, str] = {
        "thinking": "collapsed",
        "tools": "collapsed",
        "subagents": "collapsed",
        "activity": "hidden",
    }
    compose_key = "ctrl+g"
    voice_record_key = "ctrl+b"
    voice_enabled = True
    try:
        from keprix.keprix_cli.config import load_config_readonly

        cfg = load_config_readonly() or {}
        display = cfg.get("display") if isinstance(cfg, dict) else {}
        if isinstance(display, dict):
            details_cfg = display.get("details")
            if isinstance(details_cfg, dict):
                for key, value in details_cfg.items():
                    if isinstance(key, str) and isinstance(value, str):
                        details[key] = value
            compose_key = str(display.get("compose_key") or compose_key)
            voice_cfg = display.get("voice")
            if isinstance(voice_cfg, dict):
                voice_record_key = str(voice_cfg.get("record_key") or voice_record_key)
                voice_enabled = bool(voice_cfg.get("enabled", voice_enabled))
    except Exception:
        pass
    return {
        "busy_input_mode": mode,
        "busy_input_modes": list(BUSY_INPUT_MODES),
        "details": details,
        "compose_key": compose_key,
        "voice_record_key": voice_record_key,
        "voice_enabled": voice_enabled,
    }


@router.get("/api/conversations/{session_id}/turn-status")
async def turn_status(session_id: str, _user: dict = Depends(get_current_user)) -> dict[str, object]:
    return turn_registry.snapshot(session_id)


@router.post("/api/conversations/{session_id}/steer")
async def steer_turn(
    session_id: str,
    body: SteerBody,
    _user: dict = Depends(get_current_user),
) -> dict[str, object]:
    try:
        queued_chars = turn_registry.steer(session_id, body.text)
    except NotBusyError:
        raise HTTPException(status_code=409, detail={"error": "not_busy"}) from None
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True, "queued_chars": queued_chars}


@router.post("/api/conversations/{session_id}/interrupt")
async def interrupt_turn(
    session_id: str,
    body: InterruptBody | None = None,
    _user: dict = Depends(get_current_user),
) -> dict[str, object]:
    _ = body.keep_queue if body is not None else False
    turn_registry.interrupt(session_id)
    return {"ok": True}


@router.post("/api/conversations/{session_id}/clarify/{clarify_id}/respond")
async def respond_clarify(
    session_id: str,
    clarify_id: str,
    body: ClarifyRespondBody,
    _user: dict = Depends(get_current_user),
) -> dict[str, object]:
    from keprix.api.web_ui_prompt_bridge import respond_clarify as resolve_clarify

    answer = body.text if body.text is not None else body.answer
    if not resolve_clarify(clarify_id, answer):
        raise HTTPException(status_code=404, detail={"error": "clarify_not_found"})
    return {"ok": True}


@router.post("/api/conversations/{session_id}/approval/{approval_id}/respond")
async def respond_approval(
    session_id: str,
    approval_id: str,
    body: ApprovalRespondBody,
    _user: dict = Depends(get_current_user),
) -> dict[str, object]:
    from keprix.api.web_ui_prompt_bridge import respond_approval as resolve_approval

    if not resolve_approval(session_id, approval_id, body.decision):
        raise HTTPException(status_code=409, detail={"error": "approval_not_pending"})
    return {"ok": True, "status": body.decision}
