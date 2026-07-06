"""Admin user management routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from keprix.auth.dependencies import require_admin
from keprix.auth.session import auth_manager
from keprix.security.audit import audit_log

router = APIRouter(prefix="/api/admin/users", tags=["admin-users"])


class CreateUserRequest(BaseModel):
    username: str
    password: str
    email: str | None = None
    role: str = "user"
    is_approved: bool = True


class UpdateUserRequest(BaseModel):
    role: str | None = None
    is_approved: bool | None = None
    is_active: bool | None = None
    email: str | None = None


@router.post("")
async def create_user(body: CreateUserRequest, admin: dict = Depends(require_admin)) -> dict[str, Any]:
    try:
        user = auth_manager.create_user(
            body.username,
            body.password,
            role=body.role,
            email=body.email,
            is_approved=body.is_approved,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await audit_log("admin_create_user", user_id=admin.get("id"), event_data={"target": user["id"]})
    return {"user": _public_user(user)}


@router.get("")
async def list_users(admin: dict = Depends(require_admin)) -> dict[str, Any]:
    return {"users": auth_manager.list_users()}


@router.put("/{user_id}")
async def update_user(
    user_id: str,
    body: UpdateUserRequest,
    admin: dict = Depends(require_admin),
) -> dict[str, Any]:
    user = auth_manager.update_user(
        user_id,
        **{key: value for key, value in body.model_dump().items() if value is not None},
    )
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    await audit_log("admin_update_user", user_id=admin.get("id"), event_data={"target": user_id})
    return {"user": _public_user(user)}


@router.delete("/{user_id}")
async def delete_user(user_id: str, admin: dict = Depends(require_admin)) -> dict[str, bool]:
    if not auth_manager.delete_user(user_id):
        raise HTTPException(status_code=404, detail="User not found")
    await audit_log("admin_delete_user", user_id=admin.get("id"), event_data={"target": user_id})
    return {"ok": True}


def _public_user(user: dict) -> dict[str, Any]:
    return {
        "id": user.get("id"),
        "username": user.get("username"),
        "email": user.get("email"),
        "role": user.get("role", "user"),
        "is_approved": user.get("is_approved", False),
        "is_active": user.get("is_active", True),
        "totp_enabled": user.get("totp_enabled", False),
    }
