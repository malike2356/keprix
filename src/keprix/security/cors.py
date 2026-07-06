"""CORS policy for the Keprix API."""

from __future__ import annotations

from fastapi.middleware.cors import CORSMiddleware

from keprix.config.settings import get_settings

EXPOSED_HEADERS = ["X-Request-ID", "X-RateLimit-Remaining", "X-RateLimit-Reset"]


def default_local_origins() -> list[str]:
    return [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3333",
        "http://127.0.0.1:3333",
    ]


def allowed_origins() -> list[str]:
    settings = get_settings()
    if settings.allowed_origins:
        return [origin.strip() for origin in settings.allowed_origins.split(",") if origin.strip()]
    return default_local_origins()


def add_cors(app) -> None:
    origins = allowed_origins()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=EXPOSED_HEADERS,
    )
