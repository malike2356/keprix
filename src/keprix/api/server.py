"""FastAPI application factory with observability middleware and routes."""

from __future__ import annotations

import time
import uuid
from contextlib import asynccontextmanager
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, Field, field_validator
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response

from keprix.api.admin_routes import router as admin_router
from keprix.api.audio_routes import router as audio_router
from keprix.api.analytics_routes import router as analytics_router
from keprix.analytics.workspace_routes import router as analytics_workspace_router
from keprix.api.auth import PUBLIC_PATHS, require_admin  # noqa: F401 - documents public routes
from keprix.api.cron_routes import router as cron_router
from keprix.api.diagnostics_routes import router as diagnostics_router
from keprix.api.health_routes import router as health_router
from keprix.api.public_v1_routes import router as public_v1_router
from keprix.auth.admin_routes import router as admin_users_router
from keprix.auth.invite_routes import router as auth_invite_router
from keprix.auth.routes import router as auth_router
from keprix.compare.routes import router as compare_router
from keprix.evals.routes import router as evals_router
from keprix.contacts.routes import router as contacts_router
from keprix.contacts.sync.scheduler import start_contact_sync_scheduler, stop_contact_sync_scheduler
from keprix.extensions.registry import (
    get_governance_router,
    load_active_extensions,
    start_extension_hooks,
    stop_extension_hooks,
)
from keprix.contacts.sync_routes import router as contacts_sync_router
from keprix.voice_templates.routes import router as voice_templates_router
from keprix.voice.routes import router as voice_wake_router
from keprix.backend.localization.routes import router as localization_router
from keprix.backend.localization.routes_corrections import router as localization_corrections_router
from keprix.backend.notifications.routes import router as notifications_router
from keprix.backend.builder.routes import router as builder_router
from keprix.backend.domain_packs.routes import router as domain_packs_router
from keprix.backend.migration.routes import router as migration_router
from keprix.backend.messaging.routes import router as rooms_router
from keprix.backend.tools.adapters.routes import router as tool_adapters_router
from keprix.backend.evals.routes import router as eval_benchmarks_router
from keprix.backend.multiagent.routes import router as multiagent_router
from keprix.backend.control_center.routes import router as control_center_router
from keprix.backend.observability.routes import router as observability_router
from keprix.usage.routes import router as usage_router
from keprix.mobile.companion.routes import router as companion_router
from keprix.backend.intent.routes import router as intent_router
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
from keprix.opportunity.routes import router as opportunity_router
from keprix.teams.routes import router as teams_router
from keprix.agents_runtime.routes import router as agents_runtime_router
from keprix.agent.keprix.routes import router as mutation_router
from keprix.sdk.routes import router as sdk_router
from keprix.slash.routes import router as slash_router
from keprix.api.admin_workspace_routes import router as admin_workspace_router
from keprix.api.conversation_routes import router as conversation_router
from keprix.api.stats_routes import router as dashboard_stats_router
from keprix.api.dashboard_routes import router as dashboard_router
from keprix.api.admin_dashboard_routes import router as admin_dashboard_router
from keprix.ui_contract.routes import router as ui_contract_router
from keprix.coding.routes import router as coding_router
from keprix.code_agent.routes import router as code_agent_router
from keprix.typed_agents.routes import router as typed_agents_router
from keprix.interfaces.routes import router as interfaces_router
from keprix.improvement.routes import router as improvement_router
from keprix.mutation.routes import router as mutation_pipeline_router
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
from keprix.review_gateway.routes import api_router as review_gateway_router
from keprix.review_gateway.routes import public_router as review_public_router
from keprix.legal.routes import router as legal_router
from keprix.legal.middleware import LegalGateMiddleware
from keprix.browser.routes import router as browser_router
from keprix.browser.harness_routes import harness_router
from keprix.hub.routes import router as hub_router
from keprix.pack_gate.routes import router as pack_gate_router
from keprix.notify_external.routes import router as notify_external_router
from keprix.agent_apps.routes import router as agent_apps_router
from keprix.agent_apps.public_routes import router as agent_apps_public_router
from keprix.personas.routes import router as personas_router
from keprix.kernel.routes import router as kernel_router
from keprix.documents.routes import router as documents_router
from keprix.rag_pipeline.routes import router as rag_pipeline_router
from keprix.analytics.jamovi.routes import router as jamovi_router
from keprix.support.routes import router as support_router
from keprix.fleet.routes import router as fleet_router
from keprix.data_plane.routes import router as data_plane_router
from keprix.jobs.routes import router as jobs_router
from keprix.ml_workspace.routes import router as ml_workspace_router
from keprix.research_workspace.routes import router as research_workspace_router
from keprix.research_workspace.dataset_routes import router as research_dataset_router
from keprix.research_workspace.notebook_routes import router as research_notebook_router
from keprix.research_workspace.playbook_routes import router as research_playbook_router
from keprix.research_workspace.pspp_routes import router as research_pspp_router
from keprix.research_workspace.obsidian_routes import router as research_obsidian_router
from keprix.research_workspace.zotero_routes import router as research_zotero_router
from keprix.stats.routes import router as stats_router
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
    try:
        from pathlib import Path

        from keprix_cli.env_loader import load_keprix_dotenv

        load_keprix_dotenv(project_env=Path(__file__).resolve().parents[3] / ".env")
    except Exception:
        pass

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        start_email_poller()
        start_contact_sync_scheduler()
        load_active_extensions()
        from keprix.products.loader import load_products_config

        load_products_config()
        await start_extension_hooks()
        from keprix.usage.budget_alert_scheduler import start_llm_budget_alert_scheduler
        from keprix.usage.budget import ensure_budget_tables

        await ensure_budget_tables()
        start_llm_budget_alert_scheduler()
        from keprix.billing.engine import bootstrap_billing

        app.state.billing = await bootstrap_billing()
        try:
            from keprix.usage.retention import prune_llm_usage_events_async

            pruned = await prune_llm_usage_events_async()
            if pruned:
                import logging

                logging.getLogger(__name__).info("Pruned %d llm usage events on startup", pruned)
        except Exception:
            pass
        try:
            from keprix.mutation.startup import load_mutation_tools_on_startup_async

            loaded = await load_mutation_tools_on_startup_async()
            if loaded:
                import logging

                logging.getLogger(__name__).info("Loaded %d mutation tools on startup", loaded)
        except Exception:
            pass
        try:
            from keprix.mutation.retention import prune_mutations_if_due_async

            pruned = await prune_mutations_if_due_async()
            if pruned:
                import logging

                logging.getLogger(__name__).info("Pruned %d mutation records on startup", pruned)
        except Exception:
            pass
        yield
        await stop_extension_hooks()
        await stop_email_poller()
        from keprix.usage.budget_alert_scheduler import stop_llm_budget_alert_scheduler

        await stop_llm_budget_alert_scheduler()
        await stop_contact_sync_scheduler()

    app = FastAPI(title=PRODUCT_NAME,
                  version=PRODUCT_VERSION, lifespan=lifespan)
    add_cors(app)
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(StrictOriginMiddleware)
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(LegalGateMiddleware)

    from keprix.billing.config_loader import load_billing_config

    if load_billing_config() is not None:
        from keprix.billing.feature_gates.middleware import FeatureGateMiddleware
        from keprix.billing.portal.routes import router as billing_router

        app.add_middleware(FeatureGateMiddleware)
        app.include_router(billing_router)

    app.include_router(health_router)
    app.include_router(audio_router)
    app.include_router(stats_router)
    app.include_router(dashboard_router)
    app.include_router(admin_dashboard_router)
    app.include_router(conversation_router)
    app.include_router(usage_router)
    app.include_router(admin_workspace_router)
    from keprix_cli.mcp_admin_routes import router as mcp_admin_router

    app.include_router(mcp_admin_router, dependencies=[Depends(require_admin)])
    app.include_router(analytics_router)
    app.include_router(analytics_workspace_router)
    app.include_router(diagnostics_router)
    app.include_router(openai_compat_router)
    app.include_router(responses_router)
    app.include_router(models_router)
    app.include_router(embeddings_router)
    app.include_router(developer_router)
    app.include_router(mutation_router)
    app.include_router(mutation_pipeline_router)
    app.include_router(sdk_router)
    app.include_router(slash_router)
    app.include_router(ui_contract_router)
    app.include_router(coding_router)
    app.include_router(code_agent_router)
    app.include_router(typed_agents_router)
    app.include_router(interfaces_router)
    app.include_router(improvement_router)
    app.include_router(public_v1_router)
    app.include_router(admin_router)
    app.include_router(auth_router)
    app.include_router(auth_invite_router)
    app.include_router(admin_users_router)
    app.include_router(vault_router)
    app.include_router(backup_router)
    app.include_router(cron_router)
    app.include_router(export_router)
    app.include_router(privacy_router)
    app.include_router(review_gateway_router)
    app.include_router(review_public_router)
    app.include_router(legal_router)
    app.include_router(browser_router)
    app.include_router(harness_router)
    app.include_router(hub_router)
    app.include_router(pack_gate_router)
    app.include_router(agent_apps_router)
    app.include_router(agent_apps_public_router)
    app.include_router(personas_router)
    app.include_router(kernel_router)
    app.include_router(documents_router)
    app.include_router(rag_pipeline_router)
    app.include_router(jamovi_router)
    app.include_router(get_governance_router())
    app.include_router(support_router)
    app.include_router(fleet_router)
    app.include_router(data_plane_router)
    app.include_router(jobs_router)
    app.include_router(research_workspace_router)
    app.include_router(research_dataset_router)
    app.include_router(research_pspp_router)
    app.include_router(research_notebook_router)
    app.include_router(research_playbook_router)
    app.include_router(research_obsidian_router)
    app.include_router(research_zotero_router)
    app.include_router(ml_workspace_router)
    app.include_router(dashboard_stats_router)
    app.include_router(stats_router)
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
    app.include_router(opportunity_router)
    app.include_router(teams_router)
    app.include_router(agents_runtime_router)
    app.include_router(compare_router)
    app.include_router(evals_router)
    app.include_router(eval_benchmarks_router)
    app.include_router(multiagent_router)
    app.include_router(control_center_router)
    app.include_router(observability_router)
    app.include_router(playbook_router)
    app.include_router(playbook_run_router)
    app.include_router(contacts_sync_router)
    app.include_router(voice_templates_router)
    app.include_router(voice_wake_router)

    from keprix.voice.gateway_handlers import try_register_with_tui_gateway

    try_register_with_tui_gateway()
    app.include_router(localization_router)
    app.include_router(localization_corrections_router)
    app.include_router(notifications_router)
    app.include_router(builder_router)
    app.include_router(domain_packs_router)
    app.include_router(migration_router)
    app.include_router(rooms_router)
    app.include_router(tool_adapters_router)
    app.include_router(companion_router)
    app.include_router(notify_external_router)
    app.include_router(intent_router)

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
