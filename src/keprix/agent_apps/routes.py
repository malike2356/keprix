"""Agent app HTTP routes."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from starlette.background import BackgroundTask

from keprix.api.auth import require_api_auth
from keprix.agent_apps.automation import (
    delete_schedule,
    delete_webhook,
    get_schedule,
    get_webhook,
    rotate_webhook,
    upsert_schedule,
)
from keprix.agent_apps.agent_runtime import (
    AgentAppEnvError,
    AgentAppPermissionError,
    readiness_state,
)
from keprix.agent_apps.app_manifest import ManifestValidationError, load_manifest
from keprix.agent_apps.catalog import (
    get_catalog_template,
    install_catalog_template,
    list_catalog_templates,
    merge_domain_pack_templates,
)
from keprix.agent_apps.deployment_bundle import build_deployment_bundle
from keprix.agent_apps.entitlements import (
    assert_can_install,
    assert_can_install_catalog_template,
    assert_can_run,
    assert_can_schedule,
    assert_can_webhook,
    entitlement_http_detail,
    pro_templates_enabled,
    usage_summary,
)
from keprix.agent_apps.eval_runner import run_eval_suite
from keprix.agent_apps.install_bundle import max_upload_bytes, validate_uploaded_zip
from keprix.agent_apps.lifecycle import get_run_traces
from keprix.agent_apps.registry import get_agent_app_registry, sample_app_dir
from keprix.agent_apps.run_store import get_last_eval, get_run, list_run_events, list_runs, save_eval_result
from keprix.agent_apps.web_runner import run_api, run_scheduled, run_web
from keprix.security.audit import audit_log

router = APIRouter(prefix="/api/agent-apps", tags=["agent-apps"])


async def _raise_entitlement(exc: PermissionError, user: str) -> None:
    usage = await usage_summary(user)
    raise HTTPException(status_code=402, detail=entitlement_http_detail(str(exc), usage)) from exc


class RunBody(BaseModel):
    input: str = Field(default="", min_length=0)
    inputs: dict[str, Any] = Field(default_factory=dict)
    context: dict[str, Any] = Field(default_factory=dict)
    runner: str = "web"


class InstallBody(BaseModel):
    path: str


class ScheduleBody(BaseModel):
    cron: str = Field(..., min_length=1)
    timezone: str = Field(default="UTC")
    inputs: dict[str, Any] = Field(default_factory=dict)
    enabled: bool = True


def _path_install_allowed(user: str) -> bool:
    if os.environ.get("KEPRIX_DEV_MODE", "").lower() in ("1", "true", "yes"):
        return True
    return user in {"admin", "developer"}


async def _read_upload_bytes(file: UploadFile) -> bytes:
    content = await file.read()
    if len(content) > max_upload_bytes():
        raise HTTPException(
            status_code=400,
            detail=f"Bundle exceeds max upload size ({max_upload_bytes()} bytes)",
        )
    return content


@router.get("")
async def list_agent_apps(_user: str = Depends(require_api_auth)) -> dict[str, Any]:
    apps = get_agent_app_registry().list_apps()
    if not apps:
        sample = get_agent_app_registry().install(sample_app_dir(), source="template", source_id="hello-agent")
        apps = [sample]
    return {"apps": apps}


@router.get("/catalog")
async def list_catalog(
    category: str | None = None,
    q: str | None = None,
    user: str = Depends(require_api_auth),
) -> dict[str, Any]:
    templates = merge_domain_pack_templates(list_catalog_templates(category=category, query=q))
    installed = {row["name"] for row in get_agent_app_registry().list_apps()}
    pro_allowed = await pro_templates_enabled(user)
    for item in templates:
        item["installed"] = item.get("name") in installed
        item["pro_locked"] = item.get("tier") == "pro" and not pro_allowed
    return {"templates": templates}


@router.get("/catalog/{template_id}")
async def get_catalog_item(template_id: str, user: str = Depends(require_api_auth)) -> dict[str, Any]:
    item = get_catalog_template(template_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Catalog template not found")
    item["installed"] = bool(get_agent_app_registry().get(item.get("name", template_id)))
    item["pro_locked"] = item.get("tier") == "pro" and not await pro_templates_enabled(user)
    return {"template": item}


@router.post("/catalog/{template_id}/install")
async def install_catalog_item(template_id: str, user: str = Depends(require_api_auth)) -> dict[str, Any]:
    try:
        await assert_can_install_catalog_template(user, template_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        await _raise_entitlement(exc, user)
    try:
        app = install_catalog_template(template_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await audit_log(
        "agent_app.installed",
        user_id=user,
        event_data={"name": app["name"], "version": app["version"], "source": "template", "template_id": template_id},
    )
    return {"app": app, "redirect": f"/agent-apps/{app['name']}"}


@router.get("/usage")
async def agent_apps_usage(user: str = Depends(require_api_auth)) -> dict[str, Any]:
    return await usage_summary(user)


@router.get("/runs/{trace_id}")
async def agent_app_run_detail(trace_id: str, _user: str = Depends(require_api_auth)) -> dict[str, Any]:
    run = get_run(trace_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return {"run": run, "events": list_run_events(trace_id)}


@router.get("/runs/{trace_id}/events")
async def agent_app_run_events(trace_id: str, _user: str = Depends(require_api_auth)) -> dict[str, Any]:
    run = get_run(trace_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return {"trace_id": trace_id, "events": list_run_events(trace_id)}


@router.post("/install")
async def install_agent_app(body: InstallBody, user: str = Depends(require_api_auth)) -> dict[str, Any]:
    if not _path_install_allowed(user):
        raise HTTPException(
            status_code=403,
            detail="Path-based install requires KEPRIX_DEV_MODE or admin access",
        )
    try:
        await assert_can_install(user)
    except PermissionError as exc:
        await _raise_entitlement(exc, user)
    source = Path(body.path).expanduser()
    if not source.exists():
        raise HTTPException(status_code=404, detail="Agent app path not found")
    validation = get_agent_app_registry().validate_only(source)
    if not validation.get("valid"):
        raise HTTPException(status_code=400, detail=validation.get("error", "Invalid manifest"))
    app = get_agent_app_registry().install(source, source="path")
    await audit_log(
        "agent_app.installed",
        user_id=user,
        event_data={"name": app["name"], "version": app["version"], "source": "path"},
    )
    return {"app": app, "redirect": f"/agent-apps/{app['name']}"}


@router.post("/install/upload")
async def install_agent_app_upload(
    file: UploadFile = File(...),
    user: str = Depends(require_api_auth),
) -> dict[str, Any]:
    try:
        await assert_can_install(user)
    except PermissionError as exc:
        await _raise_entitlement(exc, user)
    zip_bytes = await _read_upload_bytes(file)
    registry = get_agent_app_registry()
    try:
        app = registry.install_from_zip_bytes(zip_bytes, source="upload", source_id=file.filename)
    except ManifestValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await audit_log(
        "agent_app.installed",
        user_id=user,
        event_data={"name": app["name"], "version": app["version"], "source": "upload"},
    )
    return {"app": app, "redirect": f"/agent-apps/{app['name']}"}


@router.post("/validate")
async def validate_agent_app(body: InstallBody, _user: str = Depends(require_api_auth)) -> dict[str, Any]:
    source = Path(body.path).expanduser()
    if not source.exists():
        raise HTTPException(status_code=404, detail="Agent app path not found")
    return get_agent_app_registry().validate_only(source)


@router.post("/validate/upload")
async def validate_agent_app_upload(
    file: UploadFile = File(...),
    _user: str = Depends(require_api_auth),
) -> dict[str, Any]:
    zip_bytes = await _read_upload_bytes(file)
    try:
        return validate_uploaded_zip(zip_bytes)
    except ManifestValidationError as exc:
        return {"valid": False, "error": str(exc)}


@router.get("/{app_name}")
async def get_agent_app(app_name: str, _user: str = Depends(require_api_auth)) -> dict[str, Any]:
    row = get_agent_app_registry().get(app_name)
    if row is None:
        if app_name == "hello-agent":
            row = get_agent_app_registry().install(sample_app_dir(), source="template", source_id="hello-agent")
        else:
            raise HTTPException(status_code=404, detail="Agent app not installed")
    app_dir = get_agent_app_registry().app_dir(app_name)
    if app_dir is None:
        raise HTTPException(status_code=404, detail="Agent app not installed")
    manifest = load_manifest(app_dir)
    return {"app": manifest.summary_dict()}


@router.get("/{app_name}/readiness")
async def agent_app_readiness(app_name: str, _user: str = Depends(require_api_auth)) -> dict[str, Any]:
    app_dir = get_agent_app_registry().app_dir(app_name)
    if app_dir is None:
        raise HTTPException(status_code=404, detail="Agent app not installed")
    manifest = load_manifest(app_dir)
    return readiness_state(manifest)


@router.get("/{app_name}/schedule")
async def get_agent_app_schedule(app_name: str, _user: str = Depends(require_api_auth)) -> dict[str, Any]:
    if get_agent_app_registry().app_dir(app_name) is None:
        raise HTTPException(status_code=404, detail="Agent app not installed")
    schedule = get_schedule(app_name)
    return {"schedule": schedule}


@router.post("/{app_name}/schedule")
async def upsert_agent_app_schedule(
    app_name: str,
    body: ScheduleBody,
    user: str = Depends(require_api_auth),
) -> dict[str, Any]:
    if get_agent_app_registry().app_dir(app_name) is None:
        raise HTTPException(status_code=404, detail="Agent app not installed")
    if body.enabled:
        try:
            await assert_can_schedule(user, app_name)
        except PermissionError as exc:
            await _raise_entitlement(exc, user)
    try:
        schedule = upsert_schedule(
            app_name,
            cron=body.cron,
            timezone_name=body.timezone,
            inputs=body.inputs,
            enabled=body.enabled,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await audit_log(
        "agent_app.schedule_updated",
        user_id=user,
        event_data={"name": app_name, "cron": body.cron, "enabled": body.enabled},
    )
    return {"schedule": schedule}


@router.delete("/{app_name}/schedule")
async def delete_agent_app_schedule(app_name: str, user: str = Depends(require_api_auth)) -> dict[str, Any]:
    if not delete_schedule(app_name):
        raise HTTPException(status_code=404, detail="Schedule not configured")
    await audit_log("agent_app.schedule_deleted", user_id=user, event_data={"name": app_name})
    return {"ok": True, "name": app_name}


@router.get("/{app_name}/webhook")
async def get_agent_app_webhook(
    app_name: str,
    request: Request,
    _user: str = Depends(require_api_auth),
) -> dict[str, Any]:
    if get_agent_app_registry().app_dir(app_name) is None:
        raise HTTPException(status_code=404, detail="Agent app not installed")
    webhook = get_webhook(app_name, request_base=str(request.base_url))
    return {"webhook": webhook}


@router.post("/{app_name}/webhook/rotate")
async def rotate_agent_app_webhook(
    app_name: str,
    request: Request,
    user: str = Depends(require_api_auth),
) -> dict[str, Any]:
    if get_agent_app_registry().app_dir(app_name) is None:
        raise HTTPException(status_code=404, detail="Agent app not installed")
    try:
        await assert_can_webhook(user)
    except PermissionError as exc:
        await _raise_entitlement(exc, user)
    try:
        webhook = rotate_webhook(app_name, request_base=str(request.base_url))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    await audit_log("agent_app.webhook_rotated", user_id=user, event_data={"name": app_name})
    return {"webhook": webhook}


@router.delete("/{app_name}/webhook")
async def delete_agent_app_webhook(app_name: str, user: str = Depends(require_api_auth)) -> dict[str, Any]:
    if not delete_webhook(app_name):
        raise HTTPException(status_code=404, detail="Webhook not configured")
    await audit_log("agent_app.webhook_deleted", user_id=user, event_data={"name": app_name})
    return {"ok": True, "name": app_name}


@router.get("/{app_name}/runs")
async def agent_app_runs(
    app_name: str,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    _user: str = Depends(require_api_auth),
) -> dict[str, Any]:
    if get_agent_app_registry().app_dir(app_name) is None:
        raise HTTPException(status_code=404, detail="Agent app not installed")
    return {"app": app_name, "runs": list_runs(app_name, limit=limit, offset=offset)}


@router.post("/{app_name}/run")
async def run_agent_app_route(
    app_name: str,
    body: RunBody,
    user: str = Depends(require_api_auth),
) -> dict[str, Any]:
    try:
        await assert_can_run(user)
    except PermissionError as exc:
        await _raise_entitlement(exc, user)
    app_dir = get_agent_app_registry().app_dir(app_name)
    if app_dir is None:
        if app_name == "hello-agent":
            get_agent_app_registry().install(sample_app_dir(), source="template", source_id="hello-agent")
            app_dir = get_agent_app_registry().app_dir(app_name)
    if app_dir is None:
        raise HTTPException(status_code=404, detail="Agent app not installed")
    context = dict(body.context)
    if body.inputs:
        context["form"] = body.inputs
    runner = body.runner.lower()
    try:
        if runner == "api":
            return run_api(app_dir, input_text=body.input, context=context)
        if runner == "scheduled":
            return run_scheduled(app_dir, input_text=body.input, context=context)
        return run_web(app_dir, input_text=body.input, context=context)
    except AgentAppPermissionError as exc:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "missing_permissions",
                "message": "Enable required access in Settings before running this app.",
                "missing_permissions": exc.missing,
                "settings_url": "/settings",
            },
        ) from exc
    except AgentAppEnvError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/{app_name}")
async def uninstall_agent_app(app_name: str, user: str = Depends(require_api_auth)) -> dict[str, Any]:
    if not get_agent_app_registry().uninstall(app_name):
        raise HTTPException(status_code=404, detail="Agent app not installed")
    await audit_log("agent_app.uninstalled", user_id=user, event_data={"name": app_name})
    return {"ok": True, "name": app_name}


@router.get("/{app_name}/export")
async def export_agent_app(app_name: str, _user: str = Depends(require_api_auth)) -> FileResponse:
    app_dir = get_agent_app_registry().app_dir(app_name)
    if app_dir is None:
        raise HTTPException(status_code=404, detail="Agent app not installed")
    tmp = tempfile.NamedTemporaryFile(suffix=".zip", delete=False)
    tmp_path = Path(tmp.name)
    tmp.close()
    build_deployment_bundle(app_dir, tmp_path, target="hub")
    return FileResponse(
        path=str(tmp_path),
        filename=f"{app_name}.zip",
        media_type="application/zip",
        background=BackgroundTask(lambda: tmp_path.unlink(missing_ok=True)),
    )


@router.post("/{app_name}/upgrade")
async def upgrade_agent_app(
    app_name: str,
    path: str | None = Form(default=None),
    file: UploadFile | None = File(default=None),
    user: str = Depends(require_api_auth),
) -> dict[str, Any]:
    try:
        await assert_can_install(user)
    except PermissionError as exc:
        await _raise_entitlement(exc, user)
    registry = get_agent_app_registry()
    if registry.get(app_name) is None:
        raise HTTPException(status_code=404, detail="Agent app not installed")
    try:
        if file is not None and file.filename:
            zip_bytes = await _read_upload_bytes(file)
            app = registry.upgrade_from_zip_bytes(app_name, zip_bytes, source="upload", source_id=file.filename)
        elif path:
            if not _path_install_allowed(user):
                raise HTTPException(
                    status_code=403,
                    detail="Path-based upgrade requires KEPRIX_DEV_MODE or admin access",
                )
            source = Path(path).expanduser()
            if not source.exists():
                raise HTTPException(status_code=404, detail="Agent app path not found")
            validation = registry.validate_only(source)
            if not validation.get("valid"):
                raise HTTPException(status_code=400, detail=validation.get("error", "Invalid manifest"))
            app = registry.upgrade(app_name, source, source="path")
        else:
            raise HTTPException(status_code=400, detail="Provide a zip file or path")
    except ManifestValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await audit_log(
        "agent_app.upgraded",
        user_id=user,
        event_data={"name": app["name"], "version": app["version"]},
    )
    return {"app": app, "redirect": f"/agent-apps/{app['name']}"}


@router.get("/{app_name}/traces")
async def agent_app_traces(
    app_name: str,
    trace_id: str | None = None,
    _user: str = Depends(require_api_auth),
) -> dict[str, Any]:
    return {"app": app_name, "traces": get_run_traces(app_name, trace_id=trace_id)}


@router.post("/{app_name}/evals")
async def agent_app_evals_legacy(app_name: str, user: str = Depends(require_api_auth)) -> dict[str, Any]:
    return await _run_agent_app_evals(app_name, user)


@router.post("/{app_name}/evals/run")
async def agent_app_evals_run(app_name: str, user: str = Depends(require_api_auth)) -> dict[str, Any]:
    return await _run_agent_app_evals(app_name, user)


@router.get("/{app_name}/evals/last")
async def agent_app_evals_last(app_name: str, _user: str = Depends(require_api_auth)) -> dict[str, Any]:
    if get_agent_app_registry().app_dir(app_name) is None:
        raise HTTPException(status_code=404, detail="Agent app not installed")
    last = get_last_eval(app_name)
    return {"app": app_name, "last": last}


async def _run_agent_app_evals(app_name: str, user: str) -> dict[str, Any]:
    app_dir = get_agent_app_registry().app_dir(app_name)
    if app_dir is None:
        raise HTTPException(status_code=404, detail="Agent app not installed")
    try:
        result = run_eval_suite(app_dir)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    saved = save_eval_result(app_name, result)
    await audit_log(
        "agent_app.eval_run",
        user_id=user,
        event_data={
            "name": app_name,
            "passed": result.get("passed"),
            "total": result.get("total"),
            "success": result.get("success"),
        },
    )
    return {"result": result, "last": saved}


@router.post("/{app_name}/bundle")
async def agent_app_bundle(app_name: str, _user: str = Depends(require_api_auth)) -> dict[str, Any]:
    app_dir = get_agent_app_registry().app_dir(app_name)
    if app_dir is None:
        raise HTTPException(status_code=404, detail="Agent app not installed")
    with tempfile.TemporaryDirectory() as tmp:
        output = Path(tmp) / f"{app_name}.zip"
        return build_deployment_bundle(app_dir, output, target="hub")
