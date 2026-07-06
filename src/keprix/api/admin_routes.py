"""Admin API routes for session trajectories."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from keprix.api.auth import require_admin
from keprix.observability.trajectory_exporter import (
    load_trajectory,
    summarize_trajectory,
)

router = APIRouter(prefix="/api/admin/sessions", tags=["admin"])


@router.get("/{session_id}/trajectory")
async def get_trajectory(session_id: str, _admin: str = Depends(require_admin)) -> dict:
    data = load_trajectory(session_id)
    if data is None:
        raise HTTPException(status_code=404, detail="Trajectory not found")
    return data


@router.get("/{session_id}/trajectory/summary")
async def get_trajectory_summary(session_id: str, _admin: str = Depends(require_admin)) -> dict:
    return summarize_trajectory(session_id)
