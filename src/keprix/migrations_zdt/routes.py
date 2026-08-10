"""HTTP routes for zero-downtime migration planning and gates."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from keprix.auth.dependencies import require_admin
from keprix.migrations_zdt import (
    create_add_before_drop_plan,
    create_staging_mirror,
    get_plan,
    list_plans,
    mark_staging_validated,
    production_confirmation_gate,
)

router = APIRouter(prefix="/api/migrations-zdt", tags=["migrations-zdt"])


class AddBeforeDropBody(BaseModel):
    name: str = Field(min_length=1)
    table: str = Field(min_length=1)
    oldColumn: str = Field(min_length=1)
    newColumnName: str = Field(min_length=1)
    typeSql: str = "TEXT"
    nullable: bool = True


class MirrorBody(BaseModel):
    sourceDatabase: str = "keprix"
    stagingDatabase: str = "keprix_staging"


class ProdBody(BaseModel):
    confirmToken: str = Field(min_length=1)


@router.get("")
async def list_all(user: dict = Depends(require_admin)) -> dict[str, Any]:
    _ = user
    return {"ok": True, "plans": list_plans()}


@router.post("/plan/add-before-drop")
async def plan_add(body: AddBeforeDropBody, user: dict = Depends(require_admin)) -> dict[str, Any]:
    _ = user
    try:
        plan = create_add_before_drop_plan(
            name=body.name,
            table=body.table,
            old_column=body.oldColumn,
            new_column={"name": body.newColumnName, "typeSql": body.typeSql, "nullable": body.nullable},
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True, "plan": plan}


@router.post("/staging-mirror")
async def staging_mirror(body: MirrorBody, user: dict = Depends(require_admin)) -> dict[str, Any]:
    _ = user
    return {"ok": True, "mirror": create_staging_mirror(body.sourceDatabase, body.stagingDatabase)}


@router.post("/{name}/mark-staging-validated")
async def mark_staging(name: str, user: dict = Depends(require_admin)) -> dict[str, Any]:
    _ = user
    try:
        plan = mark_staging_validated(name)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Plan not found") from exc
    return {"ok": True, "plan": plan}


@router.post("/{name}/run-production")
async def run_prod(name: str, body: ProdBody, user: dict = Depends(require_admin)) -> dict[str, Any]:
    _ = user
    plan = get_plan(name)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    gate = production_confirmation_gate(plan, body.confirmToken)
    if not gate["allowed"]:
        raise HTTPException(status_code=403, detail=gate["reason"])
    return {
        "ok": True,
        "dryRun": True,
        "gate": gate,
        "message": "Confirmation accepted. Apply via alembic/deploy tooling with the generated SQL artifacts.",
    }
