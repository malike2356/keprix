"""Feature gate matrix and enforcement."""

from __future__ import annotations

from functools import wraps
from typing import Any, Callable

from fastapi import HTTPException

from keprix.billing.config_loader import billing_enabled, load_billing_config
from keprix.billing.store import get_billing_store


async def _active_flags(user_id: str) -> dict[str, Any]:
    if not billing_enabled():
        return {"__unrestricted__": True}
    sub = await get_billing_store().get_subscription(user_id)
    if sub is None:
        cfg = load_billing_config()
        community = cfg.community_plan() if cfg else None
        return dict(community.feature_flags) if community else {}
    return dict(sub.get("feature_flags") or {})


def _value_allows(required: Any, actual: Any) -> bool:
    if actual is True:
        return True
    if actual is False or actual is None:
        return False
    if isinstance(required, str) and isinstance(actual, str):
        tiers = {"local": 1, "email": 2, "priority": 3, "full": 4}
        if required in tiers and actual in tiers:
            return tiers[actual] >= tiers[required]
        return actual == required
    if isinstance(required, (int, float)) and isinstance(actual, (int, float)):
        return actual >= required
    if isinstance(required, bool):
        return bool(actual)
    return actual == required


async def check_feature(user_id: str, feature: str, *, min_value: Any = True) -> bool:
    flags = await _active_flags(user_id)
    if flags.get("__unrestricted__"):
        return True
    if feature not in flags:
        return False
    return _value_allows(min_value, flags[feature])


def require_feature(feature: str, *, min_value: Any = True) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            user_id = str(kwargs.get("user_id") or kwargs.get("current_user", {}).get("id") or "anonymous")
            if not await check_feature(user_id, feature, min_value=min_value):
                raise HTTPException(status_code=402, detail=f"Feature not available on current plan: {feature}")
            return await func(*args, **kwargs)

        return wrapper

    return decorator
