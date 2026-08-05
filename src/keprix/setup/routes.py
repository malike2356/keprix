"""Credential setup HTTP routes."""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from keprix.auth.dependencies import get_current_user, require_admin
from keprix.security.vault_service import get_vault_service, reset_vault_service
from keprix.setup.audit import get_setup_audit
from keprix.setup.minimal import apply_minimal_setup, minimal_provider_catalog
from keprix.setup.registry import get_catalog, get_item
from keprix.setup.runtime_config import get_runtime_config
from keprix.setup.status import setup_status_snapshot
from keprix.setup.validation import validate_service
from keprix.setup.wizard import is_setup_complete, mark_setup_complete, wizard_status

router = APIRouter(prefix="/api/setup", tags=["setup"])


class SecureInputBody(BaseModel):
    service_id: str
    fields: dict[str, str] = Field(default_factory=dict)
    workspace_id: str = "default"


class ServiceActionBody(BaseModel):
    service_id: str
    workspace_id: str = "default"


class WizardStep1Body(BaseModel):
    full_name: str = ""
    email: str = Field(..., min_length=3)
    password: str = Field(..., min_length=8)


class WizardStep2Body(BaseModel):
    provider: str = Field(..., min_length=1)
    api_key: str = ""


class MinimalSetupBody(BaseModel):
    provider: str = Field(..., min_length=1)
    api_key: str = ""
    base_url: str = ""
    model: str = ""


@router.get("/wizard")
async def get_wizard_status() -> dict[str, Any]:
    return wizard_status()


@router.post("/step/{step}")
async def wizard_step(step: int, request: Request) -> dict[str, Any]:
    if is_setup_complete():
        raise HTTPException(status_code=403, detail="Setup already complete")

    if step == 0:
        return {"ok": True, "step": 0}

    if step == 1:
        body = WizardStep1Body.model_validate(await request.json())
        from keprix.auth.session import auth_manager

        ok, message = auth_manager.register(body.email, body.password, email=body.email)
        if not ok and "exists" not in message.lower():
            raise HTTPException(status_code=400, detail=message)
        return {"ok": True, "step": 1, "message": message}

    if step == 2:
        body = WizardStep2Body.model_validate(await request.json())
        if body.api_key.strip():
            item = get_item(body.provider)
            if item is None:
                raise HTTPException(status_code=404, detail="Unknown provider")
            validation = await validate_service(body.provider, {"api_key": body.api_key.strip()})
            vault = get_vault_service()
            user_id = "admin"
            secret_value = json.dumps({"api_key": body.api_key.strip()})
            vault_item = await vault.create_item(
                user_id,
                label=f"{item.name} credentials",
                value=secret_value,
                category="setup",
                tags=[body.provider],
            )
            if validation["ok"]:
                get_runtime_config().set_service(
                    body.provider,
                    vault_item_id=vault_item.id,
                    enabled=True,
                    metadata={"label": item.name},
                )
                try:
                    from keprix.agent_os.onboarding_events import record_onboarding_event

                    record_onboarding_event("admin", "provider.connected")
                except Exception:
                    pass
            return {"ok": validation["ok"], "step": 2, "validation": validation}
        return {"ok": True, "step": 2, "skipped": True}

    if step == 3:
        payload = mark_setup_complete()
        return {"ok": True, "step": 3, "setup": payload}

    raise HTTPException(status_code=422, detail=f"Invalid setup step: {step}")


@router.get("/catalog")
async def setup_catalog(_user: dict = Depends(get_current_user)) -> dict[str, Any]:
    return {"items": get_catalog()}


@router.get("/status")
async def setup_status(_user: dict = Depends(get_current_user)) -> dict[str, Any]:
    payload = setup_status_snapshot()
    payload["services"] = get_runtime_config().status()
    payload["minimal_providers"] = minimal_provider_catalog()
    return payload


@router.post("/minimal")
async def minimal_setup(body: MinimalSetupBody, _user: dict = Depends(get_current_user)) -> dict[str, Any]:
    try:
        return apply_minimal_setup(
            provider=body.provider,
            api_key=body.api_key,
            base_url=body.base_url,
            model=body.model,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None


@router.post("/secure-input")
async def secure_input(body: SecureInputBody, user: dict = Depends(require_admin)) -> dict[str, Any]:
    item = get_item(body.service_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Unknown service")
    validation = await validate_service(body.service_id, body.fields)
    vault = get_vault_service()
    user_id = str(user.get("id") or user.get("username"))
    secret_value = json.dumps(body.fields)
    vault_item = await vault.create_item(
        user_id,
        label=f"{item.name} credentials",
        value=secret_value,
        category="setup",
        tags=[body.service_id],
    )
    audit = get_setup_audit()
    status = "enabled" if validation["ok"] else "disabled"
    audit.append(
        workspace_id=body.workspace_id,
        user_id=user_id,
        service_id=body.service_id,
        action="secure_input",
        status=status,
        vault_item_id=vault_item.id,
        validation_summary=str(validation.get("summary")),
    )
    if validation["ok"]:
        get_runtime_config().set_service(
            body.service_id,
            vault_item_id=vault_item.id,
            enabled=True,
            metadata={"label": item.name},
        )
    return {
        "ok": validation["ok"],
        "service_id": body.service_id,
        "vault_item_id": vault_item.id,
        "validation": validation,
    }


@router.post("/validate")
async def validate_setup(body: SecureInputBody, _user: dict = Depends(require_admin)) -> dict[str, Any]:
    if get_item(body.service_id) is None:
        raise HTTPException(status_code=404, detail="Unknown service")
    return await validate_service(body.service_id, body.fields)


@router.post("/test")
async def test_setup(body: ServiceActionBody, user: dict = Depends(require_admin)) -> dict[str, Any]:
    user_id = str(user.get("id") or user.get("username"))
    secret = await get_runtime_config().resolve_secret(body.service_id, user_id)
    if not secret:
        raise HTTPException(status_code=404, detail="Service not configured")
    fields = json.loads(secret)
    return await validate_service(body.service_id, fields)


@router.post("/disable")
async def disable_setup(body: ServiceActionBody, user: dict = Depends(require_admin)) -> dict[str, bool]:
    ok = get_runtime_config().disable_service(body.service_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Service not configured")
    get_setup_audit().append(
        workspace_id=body.workspace_id,
        user_id=str(user.get("id") or user.get("username")),
        service_id=body.service_id,
        action="disable",
        status="disabled",
    )
    return {"ok": True}


@router.get("/audit")
async def setup_audit(_user: dict = Depends(require_admin)) -> dict[str, Any]:
    return {"events": get_setup_audit().list_rows()}


@router.get("/policy")
async def setup_policy(_user: dict = Depends(get_current_user)) -> dict[str, Any]:
    return {
        "roles": {
            "viewer": ["status"],
            "operator": ["status", "catalog"],
            "admin": ["secure_input", "validate", "disable", "test"],
            "owner": ["secure_input", "validate", "disable", "test", "delete", "policy"],
        }
    }
