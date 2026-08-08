"""HTTP ops for credential proxy doctor and Soft Wall cordon."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from keprix.auth.dependencies import require_admin
from keprix.proxy.cordon_bridge import CordonHealthCheck
from keprix.proxy.doctor import run_doctor
from keprix.proxy.paths import proxy_config_path
from keprix.proxy.pidfile import is_running, read_pid

router = APIRouter(prefix="/api/admin/proxy", tags=["credential-proxy"])


def _cordon_path() -> Path:
    path = Path.home() / ".keprix" / "proxy" / "cordon.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _read_cordon() -> dict[str, Any]:
    path = _cordon_path()
    if not path.is_file():
        return {"enabled": False}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"enabled": False}


class CordonBody(BaseModel):
    enabled: bool
    force: bool = False


@router.get("/status")
async def proxy_status(_admin: dict = Depends(require_admin)) -> dict[str, Any]:
    doctor = run_doctor()
    cordon = _read_cordon()
    health = await CordonHealthCheck().check()
    return {
        "running": is_running(),
        "pid": read_pid(),
        "config_path": str(proxy_config_path()),
        "cordon": cordon,
        "doctor": {"ok": doctor.ok, "lines": doctor.lines},
        "health": {
            "name": health.name,
            "status": health.status,
            "message": health.error,
        },
    }


@router.post("/doctor")
async def proxy_doctor(_admin: dict = Depends(require_admin)) -> dict[str, Any]:
    report = run_doctor()
    return {"ok": report.ok, "lines": report.lines}


@router.post("/cordon")
async def set_cordon(body: CordonBody, _admin: dict = Depends(require_admin)) -> dict[str, Any]:
    if not body.force:
        return {
            "blocked": True,
            "error_code": "soft_wall_required",
            "message": "Soft Wall confirm required: pass force=true to change cordon state",
            "cordon": _read_cordon(),
        }
    payload = {"enabled": bool(body.enabled)}
    _cordon_path().write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return {"blocked": False, "cordon": payload}
