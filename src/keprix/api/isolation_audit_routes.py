"""Isolation audit API routes.

Endpoints:
  GET  /api/admin/isolation-audit       - latest report + history
  POST /api/admin/isolation-audit/run   - run verifier now ({ fix?: bool })
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from keprix.auth.dependencies import require_admin
from keprix.auth.config import data_dir
from keprix.security.isolation_verifier import IsolationVerifier

router = APIRouter(prefix="/api/admin/isolation-audit", tags=["admin", "security"])

_HISTORY_LIMIT = 20


def _history_path() -> Path:
    base = Path(os.environ.get("KEPRIX_DATA_DIR") or data_dir())
    base.mkdir(parents=True, exist_ok=True)
    return base / "isolation_audit_history.json"


def _load_history() -> list[dict[str, Any]]:
    path = _history_path()
    if not path.is_file():
        return []
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return raw if isinstance(raw, list) else []
    except Exception:
        return []


def _save_history(entries: list[dict[str, Any]]) -> None:
    path = _history_path()
    path.write_text(json.dumps(entries[:_HISTORY_LIMIT], indent=2), encoding="utf-8")
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


@router.get("")
async def get_isolation_audit(_admin: dict = Depends(require_admin)) -> dict[str, Any]:
    history = _load_history()
    latest = history[0] if history else None
    return {
        "latest": latest,
        "history": history,
        "count": len(history),
    }


class IsolationRunBody(BaseModel):
    fix: bool = Field(default=False, description="Apply safe auto-fixes when available")


@router.post("/run")
async def run_isolation_audit(
    body: IsolationRunBody | None = None,
    _admin: dict = Depends(require_admin),
) -> dict[str, Any]:
    fix = bool(body.fix) if body else False
    report = await IsolationVerifier().run_all(fix=fix)
    payload = report.to_dict()
    payload["checks_run"] = [c.value for c in report.checks_run]
    history = _load_history()
    history.insert(0, payload)
    _save_history(history)
    return {"report": payload, "history_count": len(history)}
