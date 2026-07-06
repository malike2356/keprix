"""Hub marketplace HTTP routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from keprix.api.auth import require_api_auth
from keprix.hub.installer import install_pack, rollback_pack, uninstall_pack
from keprix.hub.registry import get_pack_registry
from keprix.hub.schemas import DisablePackBody, InstallPackBody, PackListResponse, PackSummary, RollbackBody
from keprix.hub.updates import available_updates
from keprix.pack_gate.deps import get_pack_gate_actor, resolve_workspace_id
from keprix.pack_gate.gate import is_gate_enabled
from keprix.pack_gate.service import after_pack_install, check_changelog_or_raise
from keprix.pack_gate.store import get_pack_gate_store

router = APIRouter(prefix="/api/hub", tags=["hub"])


def _summary(manifest, *, installed: bool = False, enabled: bool = True, source: str = "local") -> PackSummary:
    return PackSummary(
        name=manifest.name,
        version=manifest.version,
        type=manifest.type,
        author=manifest.author,
        license=manifest.license,
        description=manifest.description,
        risk_level=manifest.risk_level,
        trust_label=manifest.trust_label,
        review_score=manifest.review_score,
        installed=installed,
        enabled=enabled,
        source=source,
    )


@router.get("/packs", response_model=PackListResponse)
async def list_packs(_user: str = Depends(require_api_auth)) -> PackListResponse:
    registry = get_pack_registry()
    installed = {pack.name: pack for pack in registry.list_installed()}
    packs: list[PackSummary] = []
    templates: list[PackSummary] = []
    connectors: list[PackSummary] = []
    for manifest in registry.discover_catalog():
        inst = installed.get(manifest.name)
        summary = _summary(
            manifest,
            installed=inst is not None,
            enabled=inst.enabled if inst else True,
        )
        if manifest.type in {"app_template", "ui_template", "data_analysis_template"}:
            templates.append(summary)
        elif manifest.type == "connector_pack":
            connectors.append(summary)
        else:
            packs.append(summary)
    return PackListResponse(packs=packs, templates=templates, connectors=connectors)


@router.get("/installed")
async def list_installed(_user: str = Depends(require_api_auth)) -> dict[str, Any]:
    registry = get_pack_registry()
    return {"installed": [pack.to_dict() for pack in registry.list_installed()]}


@router.get("/updates")
async def list_updates(_user: str = Depends(require_api_auth)) -> dict[str, Any]:
    return {"updates": available_updates()}


@router.post("/install")
async def install(
    body: InstallPackBody,
    request: Request,
    response: Response,
    actor: dict = Depends(get_pack_gate_actor),
    _auth: str = Depends(require_api_auth),
) -> dict[str, Any]:
    registry = get_pack_registry()
    found = registry.find_catalog_pack(body.name, body.version)
    if found is None:
        raise HTTPException(status_code=404, detail="Pack not found in catalog")
    pack_dir, manifest = found
    workspace_id = resolve_workspace_id(request)
    config = await get_pack_gate_store().get_config(workspace_id)
    require_changelog = bool(config.get("require_changelog", True)) and await is_gate_enabled(workspace_id)
    try:
        check_changelog_or_raise(workspace_id, manifest, require_changelog)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    existing = registry.get_installed(manifest.name)
    from_version = existing.version if existing else None
    gate_active = await is_gate_enabled(workspace_id)
    result = install_pack(pack_dir, manifest, approved=body.approved, enabled=not gate_active)
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=str(result.get("message")))
    if result.get("status") != "installed":
        return result

    gate_info = await after_pack_install(
        workspace_id=workspace_id,
        manifest=manifest,
        requested_by_user_id=actor.get("id"),
        from_version=from_version,
    )
    if gate_info:
        response.status_code = 202
        return {**result, **gate_info}
    return result


@router.post("/disable")
async def disable_pack(body: DisablePackBody, _user: str = Depends(require_api_auth)) -> dict[str, Any]:
    pack = get_pack_registry().disable(body.name)
    if pack is None:
        raise HTTPException(status_code=404, detail="Pack not installed")
    return {"status": "disabled", "pack": pack.to_dict()}


@router.delete("/{name}")
async def remove_pack(name: str, _user: str = Depends(require_api_auth)) -> dict[str, Any]:
    result = uninstall_pack(name)
    if result.get("status") == "error":
        raise HTTPException(status_code=404, detail=str(result.get("message")))
    return result


@router.post("/rollback")
async def rollback(body: RollbackBody, _user: str = Depends(require_api_auth)) -> dict[str, Any]:
    result = rollback_pack(body.name, body.version)
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=str(result.get("message")))
    return result
