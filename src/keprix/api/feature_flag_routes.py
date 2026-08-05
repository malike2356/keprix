"""Admin REST API for runtime feature flag management."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from keprix.auth.dependencies import require_admin
from keprix.feature_flags.registry import FLAG_BY_ID, KNOWN_FLAGS
from keprix.feature_flags.store import FeatureFlagStore

router = APIRouter(prefix="/api/admin/feature-flags", tags=["feature-flags"])


def _runtime_defaults() -> dict[str, bool]:
    """Pull current runtime-computed defaults from the UI contract layer."""
    try:
        from keprix.api.stt_config import stt_enabled
        from keprix.governance.config import get_governance_config
        from keprix.agent_os.simplified_mode import get_simplified_mode
        from keprix.products.loader import get_product_feature_flags, load_products_config

        load_products_config()
        product_flags = get_product_feature_flags()
        return {
            "commerce": False,
            "governance": bool(get_governance_config().get().get("enabled")),
            "data_workspace": True,
            "opportunity_engine": True,
            "voice_input": stt_enabled(),
            "simplified_mode": get_simplified_mode().simplified_mode,
            **{k: bool(v) for k, v in product_flags.items()},
        }
    except Exception:
        return {f.id: f.default for f in KNOWN_FLAGS}


def _build_flag_record(flag_def: Any, overrides: dict[str, bool], runtime: dict[str, bool]) -> dict[str, Any]:
    runtime_val = runtime.get(flag_def.id, flag_def.default)
    overridden = flag_def.id in overrides
    effective = overrides[flag_def.id] if overridden else runtime_val
    return {
        "id": flag_def.id,
        "name": flag_def.name,
        "description": flag_def.description,
        "category": flag_def.category,
        "default": flag_def.default,
        "runtime_value": runtime_val,
        "overridden": overridden,
        "effective_value": effective,
        "tags": flag_def.tags,
    }


@router.get("")
async def list_feature_flags(user: dict = Depends(require_admin)) -> dict[str, Any]:
    _ = user
    store = FeatureFlagStore()
    overrides = store.load_overrides()
    runtime = _runtime_defaults()
    flags = [_build_flag_record(f, overrides, runtime) for f in KNOWN_FLAGS]
    categories = sorted({f.category for f in KNOWN_FLAGS})
    return {"flags": flags, "categories": categories, "override_count": len(overrides)}


class SetFlagBody(BaseModel):
    enabled: bool


@router.patch("/{flag_id}")
async def set_feature_flag(
    flag_id: str,
    body: SetFlagBody,
    user: dict = Depends(require_admin),
) -> dict[str, Any]:
    _ = user
    if flag_id not in FLAG_BY_ID:
        raise HTTPException(status_code=404, detail=f"Unknown feature flag: {flag_id!r}")
    FeatureFlagStore().set(flag_id, body.enabled)
    flag_def = FLAG_BY_ID[flag_id]
    runtime = _runtime_defaults()
    overrides = FeatureFlagStore().load_overrides()
    return _build_flag_record(flag_def, overrides, runtime)


@router.delete("/{flag_id}")
async def reset_feature_flag(
    flag_id: str,
    user: dict = Depends(require_admin),
) -> dict[str, Any]:
    _ = user
    if flag_id not in FLAG_BY_ID:
        raise HTTPException(status_code=404, detail=f"Unknown feature flag: {flag_id!r}")
    FeatureFlagStore().reset(flag_id)
    flag_def = FLAG_BY_ID[flag_id]
    runtime = _runtime_defaults()
    overrides = FeatureFlagStore().load_overrides()
    return _build_flag_record(flag_def, overrides, runtime)


@router.post("/reset-all")
async def reset_all_flags(user: dict = Depends(require_admin)) -> dict[str, Any]:
    _ = user
    FeatureFlagStore().reset_all()
    return {"reset": True}
