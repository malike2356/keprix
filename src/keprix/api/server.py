"""FastAPI application factory with observability middleware and routes."""

from __future__ import annotations

import time
import uuid
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, Field, field_validator
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response

from keprix.api.admin_routes import router as admin_router
from keprix.api.analytics_routes import router as analytics_router
from keprix.analytics.workspace_routes import router as analytics_workspace_router
from keprix.api.auth import PUBLIC_PATHS  # noqa: F401 - documents public routes
from keprix.api.diagnostics_routes import router as diagnostics_router
from keprix.api.health_routes import router as health_router
from keprix.api.public_v1_routes import router as public_v1_router
from keprix.auth.admin_routes import router as admin_users_router
from keprix.auth.routes import router as auth_router
from keprix.compare.routes import router as compare_router
from keprix.contacts.routes import router as contacts_router
from keprix.contacts.sync.scheduler import start_contact_sync_scheduler, stop_contact_sync_scheduler
from keprix.contacts.sync_routes import router as contacts_sync_router
from keprix.email.pollers import start_email_poller, stop_email_poller
from keprix.email.routes import router as email_router
from keprix.config.constants import PRODUCT_NAME, PRODUCT_VERSION
from keprix.config.settings import get_settings
from keprix.keys.routes import router as identity_router
from keprix.memory.rag.embedding_routes import router as embedding_router
from keprix.memory.routes import router as memory_router
from keprix.observability.request_log import get_request_log_store
from keprix.playbook.routes import router as playbook_router
from keprix.playbook.run_routes import router as playbook_run_router
from keprix.public_api.developer_routes import router as developer_router
from keprix.public_api.embeddings import router as embeddings_router
from keprix.public_api.models import router as models_router
from keprix.public_api.openai_compat import router as openai_compat_router
from keprix.public_api.responses import router as responses_router
from keprix.research.routes import router as research_router
from keprix.research.routes import search_router
from keprix.agent.keprix.routes import router as mutation_router
from keprix.sdk.routes import router as sdk_router
from keprix.slash.routes import router as slash_router
from keprix.api.admin_workspace_routes import router as admin_workspace_router
from keprix.api.conversation_routes import router as conversation_router
from keprix.api.stats_routes import router as stats_router
from keprix.api.dashboard_routes import router as dashboard_router
from keprix.ui_contract.routes import router as ui_contract_router
from keprix.coding.routes import router as coding_router
from keprix.code_agent.routes import router as code_agent_router
from keprix.interfaces.routes import router as interfaces_router
from keprix.improvement.routes import router as improvement_router
from keprix.setup.routes import router as setup_router
from keprix.security.cors import EXPOSED_HEADERS, add_cors, allowed_origins
from keprix.security.headers import SecurityHeadersMiddleware
from keprix.security.rate_limit import RateLimitMiddleware
from keprix.security.redactor import get_redactor
from keprix.security.validation import ValidationError, default_validator
from keprix.security.vault_routes import router as vault_router
from keprix.export.routes import router as export_router
import keprix.export.export_tool  # noqa: F401 - registers export_document tool on import
from keprix.privacy.routes import router as privacy_router
from keprix.scout.routes import router as scout_router
from keprix.data_plane.routes import router as data_plane_router
from keprix.skills.routes import router as skills_router
from keprix.workspace.backup_routes import router as backup_router
from keprix.workspace.routes import (
    admin_wipe_router,
    assistant_router,
    calendar_router,
    document_router,
    draft_router,
    gallery_router,
    note_router,
    personal_router,
    preset_router,
    session_router,
    task_router,
)


class StrictOriginMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        origin = request.headers.get("origin")
        if origin and origin not in allowed_origins():
            if request.method == "OPTIONS":
                return JSONResponse(status_code=403, content={"error": "Origin not allowed", "code": "forbidden"})
            return JSONResponse(status_code=403, content={"error": "Origin not allowed", "code": "forbidden"})
        return await call_next(request)


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers.setdefault("X-Request-ID", request_id)
        for header in EXPOSED_HEADERS:
            if header.lower() == "x-request-id":
                continue
        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        if not request.url.path.startswith("/api/") and not request.url.path.startswith("/v1/"):
            return await call_next(request)
        started = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - started) * 1000
        store = get_request_log_store()
        try:
            await store.log(
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_ms=duration_ms,
            )
        except Exception:
            pass
        return response


class PathCheckBody(BaseModel):
    path: str = Field(..., min_length=1)

    @field_validator("path")
    @classmethod
    def validate_path(cls, value: str) -> str:
        try:
            return default_validator.validate_path(value, "path", "/tmp/keprix-safe")
        except ValidationError as exc:
            raise ValueError(str(exc)) from exc


class RedactBody(BaseModel):
    text: str

    @field_validator("text")
    @classmethod
    def validate_text(cls, value: str) -> str:
        return default_validator.validate_string(value, "text")


class LoginBody(BaseModel):
    username: str
    password: str

    @field_validator("username", "password")
    @classmethod
    def validate_fields(cls, value: str) -> str:
        return default_validator.validate_string(value, "credential", max_length=256)


def _error_payload(status_code: int, detail: Any) -> dict[str, str]:
    if isinstance(detail, dict):
        if "error" in detail and "code" in detail:
            return {"error": str(detail["error"]), "code": str(detail["code"])}
        message = str(detail.get("detail") or detail.get("error") or detail)
    else:
        message = str(detail)
    code = "validation_error" if status_code == 422 else "http_error"
    if status_code == 401:
        code = "unauthorized"
    elif status_code == 403:
        code = "forbidden"
    elif status_code == 404:
        code = "not_found"
    elif status_code >= 500:
        code = "internal_error"
    return {"error": message, "code": code}


def create_app() -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        start_email_poller()
        start_contact_sync_scheduler()
        yield
        await stop_email_poller()
        await stop_contact_sync_scheduler()

    app = FastAPI(title=PRODUCT_NAME, version=PRODUCT_VERSION, lifespan=lifespan)
    add_cors(app)
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(StrictOriginMiddleware)
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestIdMiddleware)

    app.include_router(health_router)
    app.include_router(stats_router)
    app.include_router(dashboard_router)
    app.include_router(conversation_router)
    app.include_router(admin_workspace_router)
    app.include_router(analytics_router)
    app.include_router(analytics_workspace_router)
    app.include_router(diagnostics_router)
    app.include_router(openai_compat_router)
    app.include_router(responses_router)
    app.include_router(models_router)
    app.include_router(embeddings_router)
    app.include_router(developer_router)
    app.include_router(mutation_router)
    app.include_router(sdk_router)
    app.include_router(slash_router)
    app.include_router(ui_contract_router)
    app.include_router(coding_router)
    app.include_router(code_agent_router)
    app.include_router(interfaces_router)
    app.include_router(improvement_router)
    app.include_router(public_v1_router)
    app.include_router(admin_router)
    app.include_router(auth_router)
    app.include_router(admin_users_router)
    app.include_router(vault_router)
    app.include_router(backup_router)
    app.include_router(export_router)
    app.include_router(privacy_router)
    app.include_router(scout_router)
    app.include_router(data_plane_router)
    app.include_router(skills_router)
    app.include_router(document_router)
    app.include_router(draft_router)
    app.include_router(note_router)
    app.include_router(task_router)
    app.include_router(calendar_router)
    app.include_router(gallery_router)
    app.include_router(session_router)
    app.include_router(preset_router)
    app.include_router(assistant_router)
    app.include_router(personal_router)
    app.include_router(admin_wipe_router)
    app.include_router(identity_router)
    app.include_router(memory_router)
    app.include_router(embedding_router)
    app.include_router(email_router)
    app.include_router(contacts_router)
    app.include_router(setup_router)
    app.include_router(research_router)
    app.include_router(search_router)
    app.include_router(compare_router)
    app.include_router(playbook_router)
    app.include_router(playbook_run_router)
    app.include_router(contacts_sync_router)

    @app.exception_handler(HTTPException)
    async def http_exception_handler(_request: Request, exc: HTTPException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_payload(exc.status_code, exc.detail),
            headers=getattr(exc, "headers", None) or {},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        _request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content=_error_payload(422, exc.errors()),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(_request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content=_error_payload(500, str(exc)),
        )

    @app.post("/api/v1/security/validate-path")
    async def validate_path(body: PathCheckBody) -> dict[str, str]:
        return {"path": body.path}

    @app.post("/api/v1/security/redact")
    async def redact_output(body: RedactBody) -> dict[str, str]:
        redactor = get_redactor()
        return {"text": redactor.redact(body.text)}

    return app
