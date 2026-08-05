"""HTTP routes for Visual Playbook Studio."""

from __future__ import annotations

import os
import io
import json
import zipfile
from typing import Any

import yaml
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field
from starlette.responses import JSONResponse
from starlette.responses import Response

from keprix.playbook.canvas_compiler import CanvasCompileError, compile_canvas_document
from keprix.playbook.canvas_decompiler import decompile_playbook_document
from keprix.playbook.studio_store import PlaybookStudioStore
from keprix.playbook.version_store import PlaybookVersionStore, canonical_playbook_hash
from keprix.playbook.yaml_compiler import compile_playbook_document
from keprix.integrations.scout_lifecycle_client import emit_scout_lifecycle_event
from keprix.licensing.edition import feature_enabled
from keprix.playbook.template_catalog import get_template, list_templates, save_as_template
from keprix.playbook.workflow_coach import suggest_next_nodes
from keprix.playbook.n8n_canvas_importer import n8n_to_canvas_warnings, n8n_workflow_to_canvas

router = APIRouter(prefix="/api/playbooks/studio", tags=["playbook-studio"])
callback_router = APIRouter(prefix="/api/scout/callbacks", tags=["scout-callbacks"])


class StudioSaveRequest(BaseModel):
    canvas: dict[str, Any] | None = None
    yaml_doc: dict[str, Any] | None = Field(default=None, alias="yaml")
    layout: dict[str, Any] | None = None


class StudioCompileRequest(BaseModel):
    canvas: dict[str, Any]


class StudioDecompileRequest(BaseModel):
    yaml_text: str | None = Field(default=None, alias="yaml")
    yaml_doc: dict[str, Any] | None = None
    layout: dict[str, Any] | None = None


class StudioPublishRequest(BaseModel):
    scope: str = "personal"
    note: str | None = None
    require_scout_approval: bool = False


class ScoutPublishCallback(BaseModel):
    playbook_id: str
    version_hash: str
    decision: str
    reason: str | None = None


class StudioTemplateSaveRequest(BaseModel):
    title: str
    description: str = ""


class StudioCoachRequest(BaseModel):
    canvas: dict[str, Any]
    selected_node_id: str | None = None


class StudioImportN8nRequest(BaseModel):
    workflow: dict[str, Any]


class StudioImportYamlRequest(BaseModel):
    yaml_text: str | None = Field(default=None, alias="yaml")
    playbook_id: str | None = None


def get_studio_store() -> PlaybookStudioStore:
    return PlaybookStudioStore()


@router.get("")
async def list_studio_playbooks() -> dict[str, Any]:
    return {"playbooks": get_studio_store().list_playbooks()}


@router.get("/templates")
async def list_studio_templates() -> dict[str, Any]:
    return {"templates": list_templates()}


@router.get("/templates/{template_id}")
async def get_studio_template(template_id: str) -> dict[str, Any]:
    template = get_template(template_id)
    if template is None:
        raise HTTPException(status_code=404, detail="Template not found")
    return {"template": template, "canvas": decompile_playbook_document(template["yaml"])}


@router.post("/templates/from/{playbook_id}")
async def save_studio_template(playbook_id: str, body: StudioTemplateSaveRequest) -> dict[str, Any]:
    template_id = save_as_template(playbook_id, title=body.title, description=body.description)
    return {"template_id": template_id}


@router.post("/coach")
async def studio_coach(body: StudioCoachRequest) -> dict[str, Any]:
    selected_type = None
    if body.selected_node_id:
        for node in list(body.canvas.get("nodes") or []):
            if isinstance(node, dict) and node.get("id") == body.selected_node_id:
                selected_type = str(node.get("type") or "")
                break
    return {"suggestions": [item.to_dict() for item in suggest_next_nodes(selected_node_type=selected_type, canvas=body.canvas)]}


@router.post("/import/n8n")
async def import_n8n_canvas(body: StudioImportN8nRequest) -> dict[str, Any]:
    canvas = n8n_workflow_to_canvas(body.workflow)
    return {
        "canvas": canvas,
        "warnings": n8n_to_canvas_warnings(body.workflow),
        "suggested_id": canvas["id"],
    }


@router.post("/import/yaml")
async def import_yaml_canvas(body: StudioImportYamlRequest) -> dict[str, Any]:
    if not body.yaml_text:
        raise HTTPException(status_code=422, detail="yaml is required")
    parsed = yaml.safe_load(body.yaml_text) or {}
    compile_playbook_document(parsed)
    if body.playbook_id:
        parsed["id"] = body.playbook_id
    return {
        "canvas": decompile_playbook_document(parsed),
        "playbook_id": str(parsed.get("id") or body.playbook_id or "imported_playbook"),
    }


@router.get("/{playbook_id}")
async def get_studio_playbook(playbook_id: str) -> dict[str, Any]:
    try:
        yaml_doc, layout = get_studio_store().load(playbook_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Playbook not found") from exc
    return {
        "yaml": yaml_doc,
        "layout": layout,
        "canvas": decompile_playbook_document(yaml_doc, layout=layout),
    }


@router.put("/{playbook_id}", response_model=None)
async def save_studio_playbook(playbook_id: str, body: StudioSaveRequest):
    try:
        if body.canvas is not None:
            yaml_doc = compile_canvas_document(body.canvas)
            layout = _layout_from_canvas(body.canvas)
        elif body.yaml_doc is not None:
            yaml_doc = body.yaml_doc
            layout = body.layout
        else:
            return _compile_error([{"code": "missing_document", "message": "Provide canvas or yaml", "severity": "error"}])
        yaml_doc["id"] = playbook_id
        get_studio_store().save(playbook_id, yaml_doc, layout)
    except CanvasCompileError as exc:
        return _compile_error(exc.errors)
    return {"saved": True, "compile_errors": []}


@router.delete("/{playbook_id}")
async def delete_studio_playbook(playbook_id: str) -> dict[str, bool]:
    get_studio_store().delete(playbook_id)
    return {"deleted": True}


@router.post("/compile", response_model=None)
async def compile_studio_canvas(body: StudioCompileRequest):
    try:
        yaml_doc = compile_canvas_document(body.canvas)
    except CanvasCompileError as exc:
        return _compile_error(exc.errors)
    return {"yaml": yaml_doc, "errors": []}


@router.post("/decompile")
async def decompile_studio_yaml(body: StudioDecompileRequest) -> dict[str, Any]:
    if body.yaml_doc is not None:
        parsed = body.yaml_doc
    elif body.yaml_text:
        parsed = yaml.safe_load(body.yaml_text) or {}
    else:
        raise HTTPException(status_code=422, detail="Provide yaml or yaml_doc")
    return {"canvas": decompile_playbook_document(parsed, layout=body.layout)}


@router.post("/{playbook_id}/publish")
async def publish_studio_playbook(playbook_id: str, body: StudioPublishRequest) -> dict[str, Any]:
    try:
        yaml_doc, _layout = get_studio_store().load(playbook_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Playbook not found") from exc
    try:
        compile_playbook_document(yaml_doc)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    scope = "org" if body.scope == "org" else "personal"
    if scope == "org" and not feature_enabled("org_playbook_publish"):
        raise HTTPException(status_code=403, detail="org_publish_requires_enterprise")
    version_hash = canonical_playbook_hash(yaml_doc)
    scout_required = scope == "org" or body.require_scout_approval
    status = "pending_approval" if scout_required and _scout_enabled() else "published"
    event_type = "playbook_publish_requested" if status == "pending_approval" else "playbook_published"
    scout_event_id = await emit_scout_lifecycle_event(
        event_type,
        {
            "playbook_id": playbook_id,
            "version_hash": version_hash,
            "publisher": "local",
            "tenant": "default",
            "scope": scope,
            "yaml_preview_first_500_chars": yaml.safe_dump(yaml_doc, sort_keys=False)[:500],
            "approved_by": None if status == "pending_approval" else "auto",
        },
        workspace_id="default",
    )
    version = PlaybookVersionStore().record_publish(
        playbook_id=playbook_id,
        version_hash=version_hash,
        publisher_user_id="local",
        scope=scope,  # type: ignore[arg-type]
        status=status,  # type: ignore[arg-type]
        note=body.note or "",
        scout_event_id=scout_event_id,
    )
    return {
        "playbook_id": playbook_id,
        "version_hash": version_hash,
        "status": version.status,
        "scout_event_id": scout_event_id,
    }


@router.get("/{playbook_id}/versions")
async def list_studio_versions(playbook_id: str) -> dict[str, Any]:
    return {"versions": [version.to_dict() for version in PlaybookVersionStore().list_versions(playbook_id)]}


@router.get("/{playbook_id}/export")
async def export_studio_playbook(playbook_id: str) -> Response:
    try:
        yaml_doc, layout = get_studio_store().load(playbook_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Playbook not found") from exc
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(f"{playbook_id}.yaml", yaml.safe_dump(yaml_doc, sort_keys=False))
        archive.writestr(f"{playbook_id}.layout.json", json.dumps(layout or {}, indent=2, sort_keys=True))
        archive.writestr("README.txt", "Import this bundle on another Keprix instance. KNIME .knwf export is not supported.\n")
    return Response(
        content=buffer.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{playbook_id}.zip"'},
    )


def _layout_from_canvas(canvas: dict[str, Any]) -> dict[str, Any]:
    return {
        "positions": {
            str(node.get("id")): dict(node.get("position") or {"x": 0, "y": 0})
            for node in list(canvas.get("nodes") or [])
            if isinstance(node, dict) and node.get("id")
        },
        "viewport": dict(canvas.get("viewport") or {"x": 0, "y": 0, "zoom": 1}),
    }


def _compile_error(errors: list[dict[str, str]]) -> JSONResponse:
    return JSONResponse(status_code=422, content={"compile_errors": errors, "errors": errors})


@callback_router.post("/playbook-publish")
async def scout_playbook_publish_callback(
    body: ScoutPublishCallback,
    x_scout_callback_secret: str | None = Header(default=None),
) -> dict[str, Any]:
    expected = os.environ.get("SCOUT_CALLBACK_SECRET") or os.environ.get("LABYRINTH_SCOUT_CALLBACK_SECRET")
    if expected and x_scout_callback_secret != expected:
        raise HTTPException(status_code=401, detail="invalid_scout_callback_secret")
    if body.decision not in {"approve", "reject"}:
        raise HTTPException(status_code=422, detail="decision must be approve or reject")
    status = "published" if body.decision == "approve" else "rejected"
    try:
        version = PlaybookVersionStore().update_status(
            playbook_id=body.playbook_id,
            version_hash=body.version_hash,
            status=status,  # type: ignore[arg-type]
            note=body.reason,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Version not found") from exc
    await emit_scout_lifecycle_event(
        "playbook_published" if status == "published" else "playbook_publish_rejected",
        {
            "playbook_id": body.playbook_id,
            "version_hash": body.version_hash,
            "approved_by": "scout" if status == "published" else None,
            "reason": body.reason,
            "scope": version.scope,
        },
        workspace_id="default",
    )
    return {"playbook_id": body.playbook_id, "version_hash": body.version_hash, "status": version.status}


def _scout_enabled() -> bool:
    return os.environ.get("LABYRINTH_ENABLED") in {"1", "true", "TRUE", "yes"}
