"""FastAPI application factory with observability middleware and routes."""

from __future__ import annotations

import os
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

# Load project .env before any keprix imports that read settings/auth paths.
# AuthManager is constructed at import time; without this, login uses the wrong
# data dir and empty KEPRIX_ADMIN_* values (always "Invalid credentials").
# Also load KEPRIX_HOME/.env (GUI provider saves) so Docker Contabo sidecar
# keeps LLM keys across recreate when compose host .env drifts.


def _load_runtime_dotenv() -> None:
    try:
        from dotenv import load_dotenv
    except Exception:
        return
    try:
        load_dotenv(Path(__file__).resolve().parents[3] / ".env", override=False)
    except Exception:
        pass
    # Explicit GUI/docker SoT, then KEPRIX_HOME/.env (override so Admin Settings wins).
    candidates: list[Path] = []
    explicit = os.environ.get("KEPRIX_ENV_FILE", "").strip()
    if explicit:
        candidates.append(Path(explicit))
    home = os.environ.get("KEPRIX_HOME", "").strip()
    if home:
        candidates.append(Path(home) / ".env")
    else:
        candidates.append(Path.home() / ".keprix" / ".env")
    seen: set[str] = set()
    for path in candidates:
        key = str(path.resolve()) if path.exists() else str(path)
        if key in seen:
            continue
        seen.add(key)
        if path.is_file():
            try:
                load_dotenv(path, override=True)
            except Exception:
                pass


_load_runtime_dotenv()

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
from keprix.api.scout_dashboard_routes import router as scout_dashboard_router
from keprix.api.public_v1_routes import router as public_v1_router
from keprix.auth.admin_routes import router as admin_users_router
from keprix.auth.invite_routes import router as auth_invite_router
from keprix.auth.password_routes import router as auth_password_router
from keprix.auth.otp_routes import router as auth_otp_router
from keprix.auth.routes import router as auth_router
from keprix.api.handoff_routes import router as handoff_router
from keprix.auth.session_routes import router as auth_session_router
from keprix.auth.sso.routes import router as auth_sso_router
from keprix.compare.routes import router as compare_router
from keprix.evals.routes import router as evals_router
from keprix.contacts.routes import router as contacts_router
from keprix.contacts.sync.scheduler import start_contact_sync_scheduler, stop_contact_sync_scheduler
from keprix.api.fs_routes import router as fs_router
from keprix.workspace.calendar_sync_scheduler import start_calendar_sync_scheduler, stop_calendar_sync_scheduler
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
from keprix.api.upgrade_routes import router as upgrade_router
from keprix.api.feature_flag_routes import router as feature_flag_router
from keprix.api.self_knowledge_routes import router as self_knowledge_router
from keprix.mobile.companion.routes import router as companion_router
from keprix.backend.intent.routes import router as intent_router
from keprix.email.pollers import start_email_poller, stop_email_poller
from keprix.email.routes import router as email_router
from keprix.channel_shield.routes import email_alias_router as email_shield_router
from keprix.channel_shield.routes import router as channel_shield_router
from keprix.channel_shield.smtp_receiver import start_smtp_receiver, stop_smtp_receiver
from keprix.config.constants import PRODUCT_NAME, PRODUCT_VERSION
from keprix.config.settings import get_settings
from keprix.keys.routes import router as identity_router
from keprix.memory.rag.embedding_routes import router as embedding_router
from keprix.memory.routes import router as memory_router
from keprix.memory.hub_routes import router as memory_hub_router
from keprix.observability.request_log import get_request_log_store
from keprix.playbook.routes import router as playbook_router
from keprix.playbook.run_routes import router as playbook_run_router
from keprix.playbook.nl_builder_routes import router as playbook_nl_builder_router
from keprix.playbook.studio_routes import callback_router as playbook_scout_callback_router
from keprix.playbook.studio_routes import router as playbook_studio_router
from keprix.public_api.developer_routes import router as developer_router
from keprix.public_api.embeddings import router as embeddings_router
from keprix.public_api.models import router as models_router
from keprix.public_api.openai_compat import router as openai_compat_router
from keprix.public_api.key_actions import router as key_actions_router
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
from keprix.api.channel_config_routes import router as channel_config_router
from keprix.api.provider_config_routes import router as provider_config_router
from keprix.api.scout_config_routes import router as scout_config_router
from keprix.api.wave2_config_routes import router as wave2_config_router
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
from keprix.agent_os.routes import router as agent_os_router
from keprix.api.agent_os_skill_proposal_routes import router as agent_os_skill_proposal_router
from keprix.api.workspace_template_routes import router as workspace_template_router
from keprix.api.knowledge_vault_routes import router as knowledge_vault_router
from keprix.document_vault.routes import router as document_vault_router
from keprix.api.ladder_routes import router as ladder_router
from keprix.api.agent_os_promote_routes import router as agent_os_promote_router
from keprix.api.agent_os_ledger_routes import router as agent_os_ledger_router
from keprix.api.agent_os_board_routes import router as agent_os_board_router
from keprix.api.agent_os_run_routes import router as agent_os_run_router
from keprix.api.agent_os_client_kit_routes import router as agent_os_client_kit_router
from keprix.api.agent_os_onboarding_routes import router as agent_os_onboarding_router
from keprix.api.agent_os_onboard_routes import router as agent_os_onboard_router
from keprix.api.agent_os_maturity_routes import router as agent_os_maturity_router
from keprix.api.agent_os_connections_routes import router as agent_os_connections_router
from keprix.api.agent_os_level_up_routes import router as agent_os_level_up_router
from keprix.api.agent_os_glass_routes import router as agent_os_glass_router
from keprix.api.agent_os_milestones_routes import router as agent_os_milestones_router
from keprix.api.agent_os_phase5_routes import router as agent_os_phase5_router
from keprix.api.video_ingest_routes import router as video_ingest_router
from keprix.api.coding_preflight_routes import router as coding_preflight_router
from keprix.api.graphiti_routes import router as graphiti_router
from keprix.api.brain_activation_routes import router as brain_activation_router
from keprix.api.brain_graph_routes import router as brain_graph_router
from keprix.api.brain_health_routes import router as brain_health_router
from keprix.api.brain_session_replay_routes import router as brain_session_replay_router
from keprix.api.brain_export_routes import router as brain_export_router
from keprix.api.brain_share_routes import public_router as brain_share_public_router
from keprix.api.brain_share_routes import router as brain_share_router
from keprix.api.notebook_research_routes import router as notebook_research_router
from keprix.api.design_preview_routes import router as design_preview_router
from keprix.api.vault_pack_routes import router as vault_pack_router
from keprix.api.hot_cache_routes import router as hot_cache_router
from keprix.proxy.http_routes import router as proxy_ops_router
from keprix.api.google_workspace_routes import router as google_workspace_router
from keprix.api.agent_sync_routes import router as agent_sync_router
from keprix.api.carina_agent_routes import router as carina_agent_router
from keprix.api.keprix_kill_routes import router as keprix_kill_router
from keprix.api.syncthing_routes import router as syncthing_router
from keprix.api.credential_audit_routes import router as credential_audit_router
from keprix.api.rotation_routes import router as credential_rotation_router
from keprix.api.skill_run_routes import router as skill_run_router
from keprix.api.quota_routes import router as quota_router
from keprix.api.tool_deferred_routes import router as tool_deferred_router
from keprix.api.tool_acl_routes import router as tool_acl_router
from keprix.api.egress_audit_routes import router as egress_audit_router
from keprix.api.isolation_audit_routes import router as isolation_audit_router
from keprix.api.upstream_routes import router as upstream_router
from keprix.api.client_approval_routes import router as client_approval_router
from keprix.api.a2a_routes import router as a2a_router
from keprix.triggers.routes import router as triggers_router
from keprix.readiness.routes import router as readiness_router
from keprix.api.operator_policy_routes import router as operator_policy_router
from keprix.api.voice_routes import inbound_router as inbound_voice_router
from keprix.api.voice_routes import router as phone_voice_router
from keprix.gateway.twilio_media_stream import router as twilio_media_stream_router
from keprix.gateway.twilio_voice_handler import router as twilio_voice_router
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
from keprix.licensing.routes import router as licensing_router
from keprix.browser.routes import router as browser_router
from keprix.browser.harness_routes import harness_router
from keprix.built_apps.routes import router as built_apps_router
from keprix.hub.routes import router as hub_router
from keprix.integrations.connector_routes import router as integrations_router
from keprix.integrations.governance_routes import router as integrations_governance_router
from keprix.integrations.companies_house.routes import router as companies_house_router
from keprix.vical.routes import router as vical_router
from keprix.pack_gate.routes import router as pack_gate_router
from keprix.evidence_pack.routes import router as evidence_pack_router
from keprix.notify_external.routes import router as notify_external_router
from keprix.agent_apps.routes import router as agent_apps_router
from keprix.agent_apps.public_routes import router as agent_apps_public_router
from keprix.personas.routes import router as personas_router
from keprix.kernel.routes import router as kernel_router
from keprix.documents.routes import router as documents_router
from keprix.rag_pipeline.routes import router as rag_pipeline_router
from keprix.analytics.jamovi.routes import router as jamovi_router
from keprix.support.routes import router as support_router
from keprix.operator.routes import router as operator_router
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


def _error_payload(status_code: int, detail: Any) -> dict[str, Any]:
    """Normalize HTTP errors for API clients.

    Preserve FastAPI-style ``detail`` for structured challenges (for example
    ``totp_required``) while also exposing ``error`` / ``code`` for clients that
    expect that shape.
    """
    if isinstance(detail, dict):
        structured_code = detail.get("code")
        if isinstance(structured_code, str) and structured_code.strip():
            message = str(
                detail.get("message")
                or detail.get("error")
                or detail.get("detail")
                or structured_code
            )
            return {
                "detail": detail,
                "error": message,
                "code": structured_code,
            }
        if "error" in detail and "code" in detail:
            return {
                "error": str(detail["error"]),
                "code": str(detail["code"]),
                "detail": str(detail["error"]),
            }
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
    return {"error": message, "code": code, "detail": message}


def create_app() -> FastAPI:
    _load_runtime_dotenv()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        try:
            from keprix.email.bootstrap import ensure_email_tables

            await ensure_email_tables()
        except Exception:
            pass
        try:
            from keprix.channel_shield.bootstrap import ensure_channel_shield_tables

            await ensure_channel_shield_tables()
        except Exception:
            pass
        try:
            from keprix.contacts.bootstrap import ensure_contacts_tables

            await ensure_contacts_tables()
            from keprix.contacts.sync.scheduler import load_sync_sources_from_db

            await load_sync_sources_from_db()
        except Exception:
            pass
        try:
            from keprix.workspace.documents_pg import ensure_workspace_document_tables

            await ensure_workspace_document_tables()
        except Exception:
            pass
        try:
            from keprix.memory.schema import ensure_world_class_schema

            await ensure_world_class_schema()
        except Exception:
            pass
        try:
            from keprix.outreach.bootstrap import ensure_outreach_tables

            await ensure_outreach_tables()
        except Exception:
            pass
        try:
            from keprix.crm.bootstrap import ensure_crm_tables

            await ensure_crm_tables()
            try:
                from keprix.customer_concierge.bootstrap import ensure_concierge_tables

                await ensure_concierge_tables()
            except Exception:
                logger.exception("customer concierge bootstrap failed")
        except Exception:
            pass
        try:
            from keprix.outreach.cron_seed import ensure_outreach_cron_jobs

            ensure_outreach_cron_jobs()
        except Exception:
            pass
        try:
            from keprix.worker_kb.bootstrap import ensure_worker_kb_tables

            await ensure_worker_kb_tables()
        except Exception:
            pass
        try:
            from keprix.aiva_escalation.bootstrap import ensure_escalation_tables

            await ensure_escalation_tables()
        except Exception:
            pass
        try:
            from keprix.aiva_escalation.cron_seed import ensure_escalation_cron_jobs

            ensure_escalation_cron_jobs()
        except Exception:
            pass
        try:
            from keprix.aiva_analytics.bootstrap import ensure_analytics_tables

            await ensure_analytics_tables()
        except Exception:
            pass
        try:
            from keprix.aiva_analytics.cron_seed import ensure_analytics_cron_jobs

            ensure_analytics_cron_jobs()
        except Exception:
            pass
        start_email_poller()
        try:
            await start_smtp_receiver()
        except Exception:
            pass
        start_contact_sync_scheduler()
        try:
            start_calendar_sync_scheduler()
        except Exception:
            pass
        try:
            from keprix.vical.reminder_scheduler import start_vical_reminder_scheduler

            start_vical_reminder_scheduler()
        except Exception:
            pass
        try:
            from keprix.sync.github_bridge import start_github_bridge_schedule

            start_github_bridge_schedule()
        except Exception:
            pass
        load_active_extensions()
        from keprix.products.loader import load_products_config

        load_products_config()
        try:
            from keprix.config.health_monitor import get_health_monitor

            get_health_monitor().start_background()
        except Exception:
            pass
        await start_extension_hooks()
        from keprix.usage.budget_alert_scheduler import start_llm_budget_alert_scheduler
        from keprix.usage.budget import ensure_budget_tables

        await ensure_budget_tables()
        start_llm_budget_alert_scheduler()
        from keprix.billing.engine import bootstrap_billing

        app.state.billing = await bootstrap_billing()

        async def _deferred_maintenance() -> None:
            import logging

            log = logging.getLogger(__name__)
            try:
                from keprix.usage.retention import prune_llm_usage_events_async

                pruned = await prune_llm_usage_events_async()
                if pruned:
                    log.info("Pruned %d llm usage events on startup", pruned)
            except Exception:
                pass
            try:
                from keprix.mutation.startup import load_mutation_tools_on_startup_async

                loaded = await load_mutation_tools_on_startup_async()
                if loaded:
                    log.info("Loaded %d mutation tools on startup", loaded)
            except Exception:
                pass
            try:
                from keprix.mutation.retention import prune_mutations_if_due_async

                pruned = await prune_mutations_if_due_async()
                if pruned:
                    log.info("Pruned %d mutation records on startup", pruned)
            except Exception:
                pass

        import asyncio

        maintenance_task = asyncio.create_task(_deferred_maintenance())
        try:
            raw = os.environ.get("KEPRIX_SELF_KNOWLEDGE_BOOTSTRAP", "true").strip().lower()
            if raw not in {"0", "false", "no", "off"}:
                import asyncio
                import logging

                async def _bootstrap_self_knowledge() -> None:
                    try:
                        from keprix.self_knowledge.ingestor import SelfKnowledgeIngestor
                        result = await SelfKnowledgeIngestor(
                            include_codebase=True,
                            include_docs=True,
                            max_files=int(os.environ.get("KEPRIX_SELF_KNOWLEDGE_MAX_FILES", "1500")),
                        ).ingest()
                        logging.getLogger(__name__).info(
                            "Self-knowledge RAG indexed: %s",
                            result.to_dict(),
                        )
                    except Exception:
                        logging.getLogger(__name__).exception("Self-knowledge RAG bootstrap failed")

                asyncio.create_task(_bootstrap_self_knowledge())
        except Exception:
            pass
        trigger_tick_task = None
        try:
            import asyncio
            import logging

            from keprix.triggers.engine import tick_and_process, trigger_engine_enabled

            if trigger_engine_enabled():

                async def _trigger_ticker() -> None:
                    log = logging.getLogger(__name__)
                    while True:
                        try:
                            await asyncio.sleep(int(os.environ.get("KEPRIX_TRIGGER_TICK_SEC", "30")))
                            await tick_and_process(limit=5)
                        except asyncio.CancelledError:
                            raise
                        except Exception:
                            log.debug("trigger ticker error", exc_info=True)

                trigger_tick_task = asyncio.create_task(_trigger_ticker())
        except Exception:
            pass
        yield
        maintenance_task.cancel()
        try:
            await maintenance_task
        except Exception:
            pass
        if trigger_tick_task is not None:
            trigger_tick_task.cancel()
            try:
                await trigger_tick_task
            except Exception:
                pass
        await stop_extension_hooks()
        await stop_email_poller()
        try:
            await stop_smtp_receiver()
        except Exception:
            pass
        from keprix.usage.budget_alert_scheduler import stop_llm_budget_alert_scheduler

        await stop_llm_budget_alert_scheduler()
        try:
            from keprix.sync.github_bridge import stop_github_bridge_schedule

            stop_github_bridge_schedule()
        except Exception:
            pass
        await stop_contact_sync_scheduler()
        try:
            await stop_calendar_sync_scheduler()
        except Exception:
            pass
        try:
            from keprix.vical.reminder_scheduler import stop_vical_reminder_scheduler

            await stop_vical_reminder_scheduler()
        except Exception:
            pass

    if os.environ.get("KEPRIX_CREDENTIAL_ISOLATION_STRICT", "").lower() in {"1", "true", "yes", "on"}:
        from keprix.tools.credential_validator import validate_or_raise

        validate_or_raise()

    app = FastAPI(title=PRODUCT_NAME,
                  version=PRODUCT_VERSION, lifespan=lifespan)
    add_cors(app)
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(StrictOriginMiddleware)
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(LegalGateMiddleware)
    try:
        from keprix.security.isolation_middleware import IsolationMiddleware

        app.add_middleware(IsolationMiddleware)
    except Exception:
        pass

    from keprix.billing.config_loader import load_billing_config

    if load_billing_config() is not None:
        from keprix.billing.admin_routes import router as billing_admin_router
        from keprix.billing.feature_gates.middleware import FeatureGateMiddleware
        from keprix.billing.portal.routes import router as billing_router
        from keprix.billing.wallet.routes import router as wallet_router

        app.add_middleware(FeatureGateMiddleware)
        app.include_router(billing_router)
        app.include_router(billing_admin_router)
        app.include_router(wallet_router)

    app.include_router(health_router)
    app.include_router(scout_dashboard_router)
    app.include_router(audio_router)
    app.include_router(stats_router)
    app.include_router(dashboard_router)
    app.include_router(admin_dashboard_router)
    app.include_router(conversation_router)
    from keprix.api.tui_control_routes import router as tui_control_router
    from keprix.api.tui_slash_routes import router as tui_slash_router

    app.include_router(tui_control_router)
    app.include_router(tui_slash_router)
    app.include_router(usage_router)
    app.include_router(admin_workspace_router)
    app.include_router(channel_config_router)
    app.include_router(provider_config_router)
    app.include_router(scout_config_router)
    app.include_router(wave2_config_router)
    from keprix_cli.mcp_admin_routes import router as mcp_admin_router

    app.include_router(mcp_admin_router, dependencies=[Depends(require_admin)])
    app.include_router(analytics_router)
    app.include_router(analytics_workspace_router)
    app.include_router(diagnostics_router)
    app.include_router(openai_compat_router)
    app.include_router(responses_router)
    app.include_router(models_router)
    app.include_router(embeddings_router)
    app.include_router(key_actions_router)
    app.include_router(developer_router)
    app.include_router(mutation_router)
    app.include_router(mutation_pipeline_router)
    app.include_router(sdk_router)
    app.include_router(slash_router)
    app.include_router(ui_contract_router)
    app.include_router(coding_router)
    app.include_router(coding_preflight_router)
    app.include_router(ladder_router)
    app.include_router(code_agent_router)
    app.include_router(typed_agents_router)
    app.include_router(interfaces_router)
    app.include_router(improvement_router)
    app.include_router(agent_os_router)
    app.include_router(agent_os_skill_proposal_router)
    app.include_router(agent_os_promote_router)
    app.include_router(agent_os_ledger_router)
    app.include_router(agent_os_board_router)
    app.include_router(agent_os_run_router)
    app.include_router(agent_os_client_kit_router)
    app.include_router(agent_os_onboarding_router)
    app.include_router(agent_os_onboard_router)
    app.include_router(agent_os_maturity_router)
    app.include_router(agent_os_connections_router)
    app.include_router(agent_os_level_up_router)
    app.include_router(agent_os_glass_router)
    app.include_router(agent_os_milestones_router)
    app.include_router(agent_os_phase5_router)
    app.include_router(workspace_template_router)
    app.include_router(hot_cache_router)
    app.include_router(proxy_ops_router)
    app.include_router(google_workspace_router)
    app.include_router(agent_sync_router)
    app.include_router(carina_agent_router)
    try:
        from keprix.product_sidecar.routes import router as product_sidecar_router

        app.include_router(product_sidecar_router)
    except Exception:
        pass
    try:
        from keprix.universal_sidecar.routes import router as universal_sidecar_router

        app.include_router(universal_sidecar_router)
    except Exception:
        pass
    app.include_router(keprix_kill_router)
    try:
        from keprix.aiva_escalation.routes import router as aiva_escalation_router

        app.include_router(aiva_escalation_router)
    except Exception:
        pass
    try:
        from keprix.aiva_analytics.ui_routes import router as aiva_analytics_ui_router

        app.include_router(aiva_analytics_ui_router)
    except Exception:
        pass
    try:
        from keprix.outreach.ui_routes import router as outreach_ui_router

        app.include_router(outreach_ui_router)
    except Exception:
        pass
    try:
        from keprix.crm.routes import router as crm_router

        app.include_router(crm_router)
        try:
            from keprix.customer_concierge.routes import public_router as concierge_public_router
            from keprix.customer_concierge.routes import router as concierge_router

            app.include_router(concierge_router)
            app.include_router(concierge_public_router)
        except Exception:
            logger.exception("customer concierge routes failed to load")
        from keprix.discovery.routes import router as crm_discovery_router

        app.include_router(crm_discovery_router)
        from keprix.crm.icp_routes import router as crm_icp_router

        app.include_router(crm_icp_router)
        from keprix.crm.nice_routes import router as crm_nice_router

        app.include_router(crm_nice_router)
        from keprix.discovery import bootstrap_discovery

        try:
            bootstrap_discovery()
        except Exception:
            import logging as _logging

            _logging.getLogger(__name__).exception("discovery bootstrap failed")
    except Exception:
        import logging as _logging

        _logging.getLogger(__name__).exception("CRM / discovery routers failed to load")
    try:
        from keprix.sheet_preprocess.routes import (
            alias_router as sheet_preprocess_alias_router,
        )
        from keprix.sheet_preprocess.routes import router as sheet_preprocess_router

        app.include_router(sheet_preprocess_router)
        app.include_router(sheet_preprocess_alias_router)
    except Exception:
        pass
    try:
        from keprix.worker_kb.ui_routes import router as worker_kb_ui_router

        app.include_router(worker_kb_ui_router)
    except Exception:
        pass
    try:
        from keprix.api.scout_ops_ui_routes import router as scout_ops_ui_router

        app.include_router(scout_ops_ui_router)
    except Exception:
        pass
    app.include_router(syncthing_router)
    app.include_router(credential_audit_router)
    app.include_router(credential_rotation_router)
    app.include_router(skill_run_router)
    app.include_router(quota_router)
    app.include_router(tool_deferred_router)
    app.include_router(tool_acl_router)
    app.include_router(egress_audit_router)
    app.include_router(isolation_audit_router)
    app.include_router(upstream_router)
    app.include_router(client_approval_router)
    app.include_router(triggers_router)
    app.include_router(readiness_router)
    app.include_router(operator_policy_router)
    app.include_router(phone_voice_router)
    app.include_router(inbound_voice_router)
    app.include_router(twilio_voice_router)
    app.include_router(twilio_media_stream_router)
    app.include_router(video_ingest_router)
    app.include_router(graphiti_router)
    app.include_router(brain_activation_router)
    app.include_router(brain_graph_router)
    app.include_router(brain_health_router)
    app.include_router(brain_session_replay_router)
    app.include_router(brain_export_router)
    app.include_router(brain_share_router)
    app.include_router(brain_share_public_router)
    app.include_router(notebook_research_router)
    app.include_router(design_preview_router)
    app.include_router(public_v1_router)
    app.include_router(admin_router)
    app.include_router(auth_router)
    app.include_router(handoff_router)
    app.include_router(auth_password_router)
    app.include_router(auth_otp_router)
    app.include_router(auth_sso_router)
    app.include_router(auth_session_router)
    app.include_router(auth_invite_router)
    app.include_router(admin_users_router)
    app.include_router(vault_router)
    app.include_router(knowledge_vault_router)
    app.include_router(document_vault_router)
    app.include_router(vault_pack_router)
    app.include_router(backup_router)
    app.include_router(cron_router)
    app.include_router(export_router)
    app.include_router(privacy_router)
    app.include_router(review_gateway_router)
    app.include_router(review_public_router)
    app.include_router(legal_router)
    app.include_router(licensing_router)
    app.include_router(browser_router)
    app.include_router(harness_router)
    app.include_router(hub_router)
    app.include_router(integrations_router)
    app.include_router(integrations_governance_router)
    app.include_router(companies_house_router)
    app.include_router(vical_router)
    from keprix.tenancy.routes import router as tenancy_router

    app.include_router(tenancy_router)
    from keprix.governance.dsar_routes import router as dsar_router
    from keprix.integrations.scout_warden_routes import router as scout_warden_router
    from keprix.product_leads.routes import router as leads_router
    from keprix.billing.parity_routes import router as billing_parity_router
    from keprix.memory.rag_admin_routes import router as rag_admin_router

    app.include_router(dsar_router)
    app.include_router(scout_warden_router)
    app.include_router(leads_router)
    app.include_router(billing_parity_router)
    app.include_router(rag_admin_router)
    app.include_router(pack_gate_router)
    app.include_router(evidence_pack_router)
    app.include_router(agent_apps_router)
    app.include_router(agent_apps_public_router)
    app.include_router(built_apps_router)
    app.include_router(personas_router)
    app.include_router(kernel_router)
    app.include_router(documents_router)
    app.include_router(rag_pipeline_router)
    app.include_router(jamovi_router)
    app.include_router(get_governance_router())
    app.include_router(support_router)
    app.include_router(operator_router)
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
    app.include_router(memory_hub_router)
    app.include_router(embedding_router)
    app.include_router(email_router)
    app.include_router(channel_shield_router)
    app.include_router(email_shield_router)
    app.include_router(contacts_router)
    app.include_router(fs_router)
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
    app.include_router(a2a_router)
    app.include_router(playbook_router)
    app.include_router(playbook_run_router)
    app.include_router(playbook_nl_builder_router)
    app.include_router(playbook_studio_router)
    app.include_router(playbook_scout_callback_router)
    app.include_router(contacts_sync_router)
    app.include_router(voice_templates_router)
    app.include_router(voice_wake_router)

    from keprix.voice.gateway_handlers import try_register_with_tui_gateway

    try_register_with_tui_gateway()
    app.include_router(localization_router)
    app.include_router(localization_corrections_router)
    app.include_router(notifications_router)
    app.include_router(upgrade_router)
    app.include_router(feature_flag_router)
    app.include_router(self_knowledge_router)
    app.include_router(builder_router)
    app.include_router(domain_packs_router)
    app.include_router(migration_router)
    app.include_router(rooms_router)
    app.include_router(tool_adapters_router)
    app.include_router(companion_router)
    app.include_router(notify_external_router)
    app.include_router(intent_router)

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
