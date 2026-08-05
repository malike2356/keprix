"""Credential audit admin API."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query

from keprix.api.auth import require_admin
from keprix.tools.credential_audit import list_credential_audits
from keprix.tools.credential_contract import credential_registry
from keprix.tools.credential_validator import validate_all, validation_summary

router = APIRouter(prefix="/api/admin/credentials", tags=["admin-credentials"])


@router.get("")
async def list_credentials(limit: int = Query(default=100, ge=1, le=500), admin: dict = Depends(require_admin)) -> dict[str, Any]:
    _ = admin
    validations = validation_summary(validate_all())
    return {
        "audit": list_credential_audits(limit=limit),
        "contracts": [tool.to_dict() for tool in credential_registry.all()],
        "validation": validations,
    }
