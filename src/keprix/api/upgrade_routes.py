"""REST API for Keprix upgrade checks, wizard, alerts, and preferences."""

from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from keprix.auth.dependencies import get_current_user, require_admin
from keprix.upgrade.alerts import UpgradeAlertPreferences, UpgradeAlertStore
from keprix.upgrade.notifier import UpdateNotifier
from keprix.upgrade.scheduler import UpgradeScheduler
from keprix.upgrade.service import UpgradeService, resolve_api_product_path

router = APIRouter(prefix="/api/keprix/upgrade", tags=["keprix-upgrade"])


class TargetBody(BaseModel):
    target: str | None = None
    product_path: str | None = None
    skip_tests: bool = False
    force: bool = False


class PreferencesBody(BaseModel):
    product_path: str | None = None
    in_app_enabled: bool = True
    in_app_min_severity: str = "medium"
    email_enabled: bool = False
    email_min_severity: str = "low"
    slack_enabled: bool = False
    slack_webhook_url: str = ""
    discord_enabled: bool = False
    discord_webhook_url: str = ""
    webhook_enabled: bool = False
    webhook_url: str = ""
    quiet_hours_enabled: bool = False
    quiet_hours_start: int = 22
    quiet_hours_end: int = 7
    auto_upgrade_policy: str = "manual"
    maintenance_day: int = 6
    maintenance_hour: int = 3
    require_tests_pass: bool = True
    notify_after_upgrade: bool = True


class SnoozeBody(BaseModel):
    hours: int = Field(default=24, ge=1, le=168)


def _service(product_path: str | None = None) -> UpgradeService:
    return UpgradeService(resolve_api_product_path(product_path))


@router.get("/status")
async def upgrade_status(
    product_path: str | None = None,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    _ = user
    return _service(product_path).status()


@router.get("/check")
async def upgrade_check(
    target: str | None = None,
    product_path: str | None = None,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    _ = user
    return _service(product_path).check(target)


@router.post("/check")
async def upgrade_check_post(
    body: TargetBody,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    _ = user
    return _service(body.product_path).check(body.target)


@router.post("/check-now")
async def upgrade_check_now(
    product_path: str | None = None,
    user: dict = Depends(require_admin),
) -> dict[str, Any]:
    _ = user
    path = resolve_api_product_path(product_path)
    return UpdateNotifier(path).check_now()


@router.get("/plan")
async def upgrade_plan(
    target: str | None = None,
    product_path: str | None = None,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    _ = user
    return _service(product_path).plan(target)


@router.get("/changelog")
async def upgrade_changelog(
    target: str | None = None,
    product_path: str | None = None,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    _ = user
    return _service(product_path).changelog(target)


@router.get("/history")
async def upgrade_history(
    product_path: str | None = None,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    _ = user
    return _service(product_path).history()


@router.get("/wizard")
async def upgrade_wizard_preview(
    target: str,
    product_path: str | None = None,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    _ = user
    service = _service(product_path)
    return {
        "target": target,
        "steps": service.wizard_steps(target),
        "check": service.check(target),
        "changelog": service.changelog(target),
    }


@router.post("/dry-run")
async def upgrade_dry_run(
    body: TargetBody,
    user: dict = Depends(require_admin),
) -> dict[str, Any]:
    _ = user
    if not body.target:
        raise HTTPException(status_code=400, detail="target is required")
    svc = _service(body.product_path)
    target = body.target
    skip = body.skip_tests
    return await asyncio.to_thread(lambda: svc.dry_run(target, skip_tests=skip))


@router.post("/execute")
async def upgrade_execute(
    body: TargetBody,
    user: dict = Depends(require_admin),
) -> dict[str, Any]:
    _ = user
    if not body.target:
        raise HTTPException(status_code=400, detail="target is required")
    svc = _service(body.product_path)
    target = body.target
    force = body.force
    return await asyncio.to_thread(lambda: svc.execute(target, force=force))


@router.post("/rollback")
async def upgrade_rollback(
    body: TargetBody,
    user: dict = Depends(require_admin),
) -> dict[str, Any]:
    _ = user
    return _service(body.product_path).rollback(force=body.force)


@router.get("/alerts")
async def list_alerts(
    product_path: str | None = None,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    _ = user
    store = UpgradeAlertStore(resolve_api_product_path(product_path))
    return {"alerts": [alert.to_dict() for alert in store.list_alerts()]}


@router.get("/modules")
async def list_modules(
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    """Surface shipped modules and whether each has a GUI route yet."""
    _ = user
    from keprix.upgrade.gui_catalog import modules_payload

    return modules_payload()


@router.post("/alerts/{alert_id}/dismiss")
async def dismiss_alert(
    alert_id: str,
    product_path: str | None = None,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    _ = user
    store = UpgradeAlertStore(resolve_api_product_path(product_path))
    if not store.dismiss_alert(alert_id):
        raise HTTPException(status_code=404, detail="alert not found")
    return {"dismissed": True}


@router.post("/alerts/{alert_id}/snooze")
async def snooze_alert(
    alert_id: str,
    body: SnoozeBody,
    product_path: str | None = None,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    _ = user
    store = UpgradeAlertStore(resolve_api_product_path(product_path))
    if not store.snooze_alert(alert_id, hours=body.hours):
        raise HTTPException(status_code=404, detail="alert not found")
    return {"snoozed": True, "hours": body.hours}


@router.get("/notifications/preferences")
async def get_preferences(
    product_path: str | None = None,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    _ = user
    store = UpgradeAlertStore(resolve_api_product_path(product_path))
    return {"preferences": store.load_preferences().to_dict()}


@router.put("/notifications/preferences")
async def put_preferences(
    body: PreferencesBody,
    user: dict = Depends(require_admin),
) -> dict[str, Any]:
    _ = user
    store = UpgradeAlertStore(resolve_api_product_path(body.product_path))
    prefs = UpgradeAlertPreferences.from_dict(body.model_dump(exclude={"product_path"}))
    return {"preferences": store.save_preferences(prefs).to_dict()}


@router.get("/scheduler")
async def get_scheduler(
    product_path: str | None = None,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    _ = user
    scheduler = UpgradeScheduler(resolve_api_product_path(product_path))
    return {"preferences": scheduler.load_preferences().to_dict()}


@router.put("/scheduler")
async def put_scheduler(
    body: PreferencesBody,
    user: dict = Depends(require_admin),
) -> dict[str, Any]:
    _ = user
    scheduler = UpgradeScheduler(resolve_api_product_path(body.product_path))
    prefs = UpgradeAlertPreferences.from_dict(body.model_dump(exclude={"product_path"}))
    return {"preferences": scheduler.save_preferences(prefs).to_dict()}
