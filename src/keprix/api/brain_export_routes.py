"""Brain graph export API routes."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import Response

from keprix.auth.dependencies import get_current_user
from keprix.brain.export_csv import export_brain_edges_csv, export_brain_nodes_csv
from keprix.brain.export_json import export_brain_json
from keprix.brain.export_obsidian import export_brain_obsidian

router = APIRouter(prefix="/api/brain/export", tags=["brain-export"])


def _workspace_id(workspace_id: str | None, user: dict[str, Any]) -> str:
    return workspace_id or str(user.get("workspace_id") or "default")


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d")


@router.get("/json")
async def export_json(
    workspace_id: str | None = None,
    user: dict[str, Any] = Depends(get_current_user),
) -> Response:
    resolved = _workspace_id(workspace_id, user)
    payload = await export_brain_json(resolved)
    filename = f"brain-{resolved}-{_stamp()}.json"
    return Response(
        content=json.dumps(payload, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/obsidian")
async def export_obsidian(
    workspace_id: str | None = None,
    user: dict[str, Any] = Depends(get_current_user),
) -> Response:
    resolved = _workspace_id(workspace_id, user)
    archive = await export_brain_obsidian(resolved)
    filename = f"brain-obsidian-{_stamp()}.zip"
    return Response(
        content=archive,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/csv")
async def export_csv_nodes(
    workspace_id: str | None = None,
    user: dict[str, Any] = Depends(get_current_user),
) -> Response:
    resolved = _workspace_id(workspace_id, user)
    content = await export_brain_nodes_csv(resolved)
    filename = f"brain-nodes-{_stamp()}.csv"
    return Response(
        content=content,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/csv/edges")
async def export_csv_edges(
    workspace_id: str | None = None,
    user: dict[str, Any] = Depends(get_current_user),
) -> Response:
    resolved = _workspace_id(workspace_id, user)
    content = await export_brain_edges_csv(resolved)
    filename = f"brain-edges-{_stamp()}.csv"
    return Response(
        content=content,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
