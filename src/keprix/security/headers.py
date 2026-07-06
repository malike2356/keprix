"""HTTP security headers middleware."""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from keprix.config.settings import get_settings


def build_security_headers(*, https_enabled: bool = False) -> dict[str, str]:
    settings = get_settings()
    csp = "default-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
    if settings.csp_extra:
        csp = f"{csp}; {settings.csp_extra.strip().rstrip(';')}"
    headers = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
        "Content-Security-Policy": csp,
    }
    if https_enabled or settings.secure_cookies:
        headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return headers


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        https_enabled = request.url.scheme == "https"
        for key, value in build_security_headers(https_enabled=https_enabled).items():
            response.headers.setdefault(key, value)
        return response
