"""Attach billing feature flags to each authenticated request."""

from __future__ import annotations

from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from keprix.billing.config_loader import billing_enabled
from keprix.billing.feature_gates.enforcer import _active_flags


class FeatureGateMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        if billing_enabled():
            user = getattr(request.state, "user", None)
            if isinstance(user, dict):
                user_id = str(user.get("id") or user.get("username") or "anonymous")
                flags: dict[str, Any] = await _active_flags(user_id)
                request.state.billing_flags = flags
        return await call_next(request)
