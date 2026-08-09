"""Capability node handlers for Carina/Aiva product pack."""

from __future__ import annotations

import logging
import time
from collections.abc import Awaitable, Callable
from typing import Any

from keprix.product_sidecar.state import (
    get_approval_store,
    get_job_store,
    get_kill_switches,
    get_memory_store,
    get_shadow_store,
    input_hash,
)
from keprix.product_sidecar.types import RequestContext

Handler = Callable[[RequestContext, dict[str, Any]], Awaitable[dict[str, Any]]]
logger = logging.getLogger(__name__)


def _deep_link(product: str, kind: str, approval_id: str) -> str:
    if product == "aiva":
        return f"/aiva/soft-wall?approval_id={approval_id}&kind={kind}"
    return f"/crm/soft-wall?approval_id={approval_id}&kind={kind}"


async def handle_agent_run(ctx: RequestContext, payload: dict[str, Any]) -> dict[str, Any]:
    if ctx.shadow:
        # Shadow: never publish side effects; return comparison-safe stub reply.
        get_shadow_store().record(
            {
                "workspace_id": ctx.workspace_id,
                "node_key": "agent.run",
                "shadow": True,
                "tool_calls": [],
                "latency_ms": 1,
                "refusal": None,
            }
        )
        return {
            "message": {
                "role": "assistant",
                "content": "[shadow] comparison-only response; not published",
            },
            "tool_calls": [],
            "finish_reason": "stop",
            "session_id": ctx.session_id or str(payload.get("session_id") or ""),
            "shadow": True,
            "side_effects": False,
        }

    from keprix.agent.carina_bridge import CarinaAgentBridge
    from keprix.security.aiva_scout import get_aiva_scout_guard

    model = str(payload.get("model") or "deepseek-v4-pro")
    route = None
    system_prompt = str(payload.get("system_prompt") or "")
    inject_worker_kb = payload.get("inject_worker_kb", True) is not False
    if ctx.product == "aiva":
        from keprix.aiva.model_routing import resolve_aiva_model
        from keprix.aiva.system_prompt import build_aiva_system_prompt

        route = resolve_aiva_model(
            workspace_id=ctx.workspace_id,
            tier=str(payload.get("aiva_tier") or payload.get("billing_tier") or "starter"),
            workspace_model=(
                str(payload["workspace_model"]).strip() if payload.get("workspace_model") else None
            ),
            workspace_provider=(
                str(payload["workspace_provider"]).strip()
                if payload.get("workspace_provider")
                else None
            ),
            require_tools=bool(payload.get("tools") or payload.get("carina_tools")),
        )
        model = route.model_id

        # Replace fat Carina/engineering system prompts with the lean Aiva persona.
        caller_prompt = system_prompt.strip()
        domain_knowledge = str(payload.get("domain_knowledge") or "").strip()
        if caller_prompt and len(caller_prompt) < 2500 and "verlox monorepo" not in caller_prompt.lower():
            # Short caller text is treated as extra domain knowledge, not a full system prompt.
            if not domain_knowledge:
                domain_knowledge = caller_prompt
        overrides = payload.get("aiva_workspace_overrides") or payload.get("workspace_overrides") or {}
        if not isinstance(overrides, dict):
            overrides = {}
        system_prompt = build_aiva_system_prompt(
            aiva_name=(str(payload["aiva_name"]).strip() if payload.get("aiva_name") else None),
            user_name=(str(payload["user_name"]).strip() if payload.get("user_name") else None),
            tone=(str(payload["tone"]).strip() if payload.get("tone") else None),
            domain=(str(payload.get("aiva_domain") or payload.get("domain") or "").strip() or None),
            tools=payload.get("tools") or payload.get("carina_tools") or [],
            memory_injection=(
                str(payload["memory_injection"]).strip() if payload.get("memory_injection") else None
            ),
            calendar_today=(
                str(payload["calendar_today"]).strip() if payload.get("calendar_today") else None
            ),
            recent_emails_summary=(
                str(payload["recent_emails_summary"]).strip()
                if payload.get("recent_emails_summary")
                else None
            ),
            domain_knowledge=domain_knowledge or None,
            workspace_overrides=overrides,
        )
        # Worker KB can re-inflate the prompt; Aiva lean path opts out unless asked.
        if "inject_worker_kb" not in payload:
            inject_worker_kb = False

    bridge = CarinaAgentBridge()
    started = time.perf_counter()
    result = await bridge.run(
        workspace_id=ctx.workspace_id,
        session_id=payload.get("session_id") or ctx.session_id,
        model=model,
        temperature=float(payload.get("temperature", 0.7)),
        system_prompt=system_prompt,
        messages=payload.get("messages") or [],
        tools=payload.get("tools") or [],
        carina_tools=payload.get("carina_tools") or [],
        scout=get_aiva_scout_guard(),
        worker_id=(str(payload["worker_id"]).strip() if payload.get("worker_id") else None),
        inject_worker_kb=inject_worker_kb,
        product=ctx.product,
        confidence=(
            float(payload["confidence"])
            if payload.get("confidence") is not None and str(payload.get("confidence")).strip() != ""
            else None
        ),
        force_escalate=bool(payload.get("force_escalate")),
        escalation_enabled=payload.get("escalation_enabled", True) is not False,
    )
    duration_ms = int((time.perf_counter() - started) * 1000)
    if route is not None:
        logger.info(
            "Aiva model call workspace=%s tier=%s provider=%s model=%s duration_ms=%d target_ms=%d",
            ctx.workspace_id,
            route.tier,
            route.provider,
            route.model,
            duration_ms,
            route.latency_target_ms,
        )
        if isinstance(result, dict):
            result["model_routing"] = {
                "provider": route.provider,
                "model": route.model,
                "tier": route.tier,
                "source": route.source,
                "duration_ms": duration_ms,
                "latency_target_ms": route.latency_target_ms,
            }
    return result


async def handle_agent_interrupt(ctx: RequestContext, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "interrupted": True,
        "workspace_id": ctx.workspace_id,
        "session_id": payload.get("session_id") or ctx.session_id,
    }


async def handle_soft_wall_request(ctx: RequestContext, payload: dict[str, Any]) -> dict[str, Any]:
    node_key = str(payload.get("node_key") or "soft_wall.request")
    ih = input_hash(payload.get("action") or payload)
    row = get_approval_store().request(
        product=ctx.product,
        workspace_id=ctx.workspace_id,
        node_key=node_key,
        input_hash=ih,
        reason=str(payload.get("reason") or "operator approval required"),
        deep_link=_deep_link(ctx.product, node_key, "pending"),
    )
    row["deep_link"] = _deep_link(ctx.product, node_key, row["approval_id"])
    return {"approval": row, "soft_wall_bus": "product"}


async def handle_soft_wall_status(ctx: RequestContext, payload: dict[str, Any]) -> dict[str, Any]:
    approval_id = str(payload.get("approval_id") or "")
    row = get_approval_store().get(approval_id)
    if not row or row["workspace_id"] != ctx.workspace_id:
        return {"found": False}
    return {"found": True, "approval": row}


async def handle_crm_search(ctx: RequestContext, payload: dict[str, Any]) -> dict[str, Any]:
    query = str(payload.get("query") or "").strip()
    try:
        from keprix.crm import store as crm_store

        # Projected: ids + display fields only; never dump tenant.
        contacts = []
        if hasattr(crm_store, "search_contacts"):
            contacts = crm_store.search_contacts(ctx.workspace_id, query=query, limit=25)  # type: ignore[attr-defined]
        return {
            "workspace_id": ctx.workspace_id,
            "query": query,
            "results": contacts if isinstance(contacts, list) else [],
            "projected": True,
        }
    except Exception:
        return {
            "workspace_id": ctx.workspace_id,
            "query": query,
            "results": [],
            "projected": True,
            "note": "crm_store_unavailable_stub",
        }


async def _require_soft_wall(
    ctx: RequestContext, payload: dict[str, Any], node_key: str
) -> dict[str, Any] | None:
    """Return soft_wall_required payload or None if approved / shadow-blocked."""
    if ctx.shadow:
        return {
            "error": "soft_wall_required",
            "code": "soft_wall_required",
            "shadow_blocked": True,
            "message": "Shadow path cannot mutate or outbound",
        }
    if get_kill_switches().outbound_kill and node_key.split(".")[0] in {
        "crm",
        "outreach",
        "channels",
        "data",
    }:
        return {"error": "denied", "code": "denied", "reason": "outbound_kill"}

    approval_id = str(payload.get("approval_id") or "").strip()
    ih = input_hash({k: v for k, v in payload.items() if k != "approval_id"})
    if approval_id and get_approval_store().is_approved(
        approval_id, workspace_id=ctx.workspace_id, input_hash=ih
    ):
        return None

    row = get_approval_store().request(
        product=ctx.product,
        workspace_id=ctx.workspace_id,
        node_key=node_key,
        input_hash=ih,
        reason=f"Soft Wall required for {node_key}",
        deep_link="",
    )
    deep = _deep_link(ctx.product, node_key, row["approval_id"])
    row["deep_link"] = deep
    return {
        "error": "soft_wall_required",
        "code": "soft_wall_required",
        "approval_id": row["approval_id"],
        "reason": row["reason"],
        "deep_link": deep,
        "input_hash": ih,
    }


async def handle_crm_propose(ctx: RequestContext, payload: dict[str, Any]) -> dict[str, Any]:
    blocked = await _require_soft_wall(ctx, payload, "crm.propose")
    if blocked:
        return blocked
    return {
        "proposed": True,
        "workspace_id": ctx.workspace_id,
        "proposal": payload.get("proposal") or {},
        "applied": False,
        "note": "Product SoT apply via southbound connector with approval evidence",
    }


async def handle_crm_enroll(ctx: RequestContext, payload: dict[str, Any]) -> dict[str, Any]:
    blocked = await _require_soft_wall(ctx, payload, "crm.enroll")
    if blocked:
        return blocked
    list_id = str(payload.get("list_id") or "")
    try:
        from keprix.crm.enroll import enroll_list

        result = enroll_list(
            workspace_id=ctx.workspace_id,
            list_id=list_id,
            actor_id=ctx.actor_id,
            approval_id=str(payload.get("approval_id") or ""),
            force=False,
        )
        return {"enrolled": True, "result": result}
    except Exception as exc:
        return {
            "enrolled": False,
            "list_id": list_id,
            "note": "enroll_handler_deferred",
            "detail": str(exc)[:200],
            "idempotency_key": payload.get("idempotency_key"),
        }


async def handle_crm_pipeline_read(ctx: RequestContext, payload: dict[str, Any]) -> dict[str, Any]:
    return {"workspace_id": ctx.workspace_id, "pipeline": [], "projected": True}


async def handle_crm_analytics(ctx: RequestContext, payload: dict[str, Any]) -> dict[str, Any]:
    return {"workspace_id": ctx.workspace_id, "summary": {"deals": 0, "enrolled": 0}}


async def handle_discovery_job(ctx: RequestContext, payload: dict[str, Any]) -> dict[str, Any]:
    blocked = await _require_soft_wall(ctx, payload, "discovery.jobs.create")
    if blocked:
        return blocked
    job = get_job_store().create(
        product=ctx.product,
        workspace_id=ctx.workspace_id,
        node_key="discovery.jobs.create",
        input_payload=payload,
        idempotency_key=str(payload.get("idempotency_key") or ""),
    )
    get_job_store().mark_running(job["job_id"])
    get_job_store().complete(job["job_id"], {"queued_targets": 0})
    return {"job": get_job_store().get(job["job_id"], workspace_id=ctx.workspace_id)}


async def handle_outreach_enqueue(ctx: RequestContext, payload: dict[str, Any]) -> dict[str, Any]:
    blocked = await _require_soft_wall(ctx, payload, "outreach.outbox.enqueue")
    if blocked:
        return blocked
    key = str(payload.get("idempotency_key") or input_hash(payload))
    from keprix.product_sidecar.state import get_circuit

    existing = get_circuit().get_side_effect(key)
    if existing:
        return existing
    result = {"enqueued": True, "idempotency_key": key, "workspace_id": ctx.workspace_id}
    return get_circuit().remember_side_effect(key, result)


async def handle_vical_offer(ctx: RequestContext, payload: dict[str, Any]) -> dict[str, Any]:
    blocked = await _require_soft_wall(ctx, payload, "vical.booking.offer")
    if blocked:
        return blocked
    return {
        "offer_id": f"offer_{ctx.workspace_id[:8]}",
        "workspace_id": ctx.workspace_id,
        "artifact": "product_visible",
        "status": "proposed",
    }


async def handle_booking_status(ctx: RequestContext, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "offer_id": payload.get("offer_id"),
        "workspace_id": ctx.workspace_id,
        "status": "unknown",
    }


async def handle_scout_hook(ctx: RequestContext, payload: dict[str, Any]) -> dict[str, Any]:
    # Allowlisted fields only; no raw PII dump.
    event = {
        "type": str(payload.get("type") or "agent.turn"),
        "workspace_id": ctx.workspace_id,
        "correlation_id": ctx.correlation_id,
        "redacted": True,
    }
    return {"emitted": True, "event": event}


async def handle_memory_get(ctx: RequestContext, payload: dict[str, Any]) -> dict[str, Any]:
    key = str(payload.get("key") or "")
    row = get_memory_store().get(product=ctx.product, workspace_id=ctx.workspace_id, key=key)
    return {"found": row is not None, "entry": row}


async def handle_memory_put(ctx: RequestContext, payload: dict[str, Any]) -> dict[str, Any]:
    durable = not ctx.shadow and str(payload.get("authority") or "wave2") == "wave2"
    if ctx.shadow:
        durable = False
    key = str(payload.get("key") or "")
    value = payload.get("value") if isinstance(payload.get("value"), dict) else {"text": payload.get("value")}
    row = get_memory_store().put(
        product=ctx.product,
        workspace_id=ctx.workspace_id,
        key=key,
        value=value or {},
        durable=durable,
        provenance={
            "correlation_id": ctx.correlation_id,
            "actor_id": ctx.actor_id,
            "shadow": ctx.shadow,
        },
    )
    return {"stored": True, "durable": durable, "entry": row}


async def handle_rag_search(ctx: RequestContext, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "workspace_id": ctx.workspace_id,
        "query": payload.get("query"),
        "hits": [],
        "scoped": True,
    }


async def handle_playbook_start(ctx: RequestContext, payload: dict[str, Any]) -> dict[str, Any]:
    blocked = await _require_soft_wall(ctx, payload, "playbook.start")
    if blocked:
        return blocked
    job = get_job_store().create(
        product=ctx.product,
        workspace_id=ctx.workspace_id,
        node_key="playbook.start",
        input_payload=payload,
        idempotency_key=str(payload.get("idempotency_key") or ""),
    )
    return {"job": job, "playbook": payload.get("playbook_id"), "term": "Playbook"}


async def handle_playbook_status(ctx: RequestContext, payload: dict[str, Any]) -> dict[str, Any]:
    job_id = str(payload.get("job_id") or "")
    job = get_job_store().get(job_id, workspace_id=ctx.workspace_id)
    return {"job": job, "term": "Playbook"}


async def handle_jobs_create(ctx: RequestContext, payload: dict[str, Any]) -> dict[str, Any]:
    job = get_job_store().create(
        product=ctx.product,
        workspace_id=ctx.workspace_id,
        node_key="jobs.create",
        input_payload=payload,
        idempotency_key=str(payload.get("idempotency_key") or ""),
    )
    return {"job": job}


async def handle_jobs_cancel(ctx: RequestContext, payload: dict[str, Any]) -> dict[str, Any]:
    job_id = str(payload.get("job_id") or "")
    job = get_job_store().cancel(job_id, workspace_id=ctx.workspace_id)
    return {"job": job, "idempotent": True}


async def handle_channels_notify(ctx: RequestContext, payload: dict[str, Any]) -> dict[str, Any]:
    blocked = await _require_soft_wall(ctx, payload, "channels.notify")
    if blocked:
        return blocked
    return {"notified": True, "channel": payload.get("channel") or "telegram_operator"}


async def handle_data_datasets_list(ctx: RequestContext, payload: dict[str, Any]) -> dict[str, Any]:
    return {"workspace_id": ctx.workspace_id, "datasets": [], "scoped": True}


async def handle_data_jobs_create(ctx: RequestContext, payload: dict[str, Any]) -> dict[str, Any]:
    blocked = await _require_soft_wall(ctx, payload, "data.jobs.create")
    if blocked:
        return blocked
    job = get_job_store().create(
        product=ctx.product,
        workspace_id=ctx.workspace_id,
        node_key="data.jobs.create",
        input_payload=payload,
        idempotency_key=str(payload.get("idempotency_key") or ""),
    )
    return {"job": job}


async def handle_data_export(ctx: RequestContext, payload: dict[str, Any]) -> dict[str, Any]:
    blocked = await _require_soft_wall(ctx, payload, "data.export")
    if blocked:
        return blocked
    target_ws = str(payload.get("target_workspace_id") or ctx.workspace_id)
    if target_ws != ctx.workspace_id:
        return {"error": "denied", "code": "denied", "reason": "cross_workspace_export"}
    return {"exported": True, "workspace_id": ctx.workspace_id}


async def handle_not_configured(ctx: RequestContext, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "error": "not_configured",
        "code": "not_configured",
        "message": "Owner credentials / legal clearance required",
    }


async def handle_ops_probe(ctx: RequestContext, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "ok": True,
        "primary_invoke_path": True,
        "product": ctx.product,
        "workspace_id": ctx.workspace_id,
        "note": "OPS honesty probe succeeded",
    }


HANDLERS: dict[str, Handler] = {
    "agent.run": handle_agent_run,
    "agent.interrupt": handle_agent_interrupt,
    "soft_wall.request": handle_soft_wall_request,
    "soft_wall.status": handle_soft_wall_status,
    "crm.search": handle_crm_search,
    "crm.propose": handle_crm_propose,
    "crm.enroll": handle_crm_enroll,
    "crm.pipeline.read": handle_crm_pipeline_read,
    "crm.analytics.summary": handle_crm_analytics,
    "discovery.jobs.create": handle_discovery_job,
    "outreach.outbox.enqueue": handle_outreach_enqueue,
    "vical.booking.offer": handle_vical_offer,
    "booking.status": handle_booking_status,
    "scout.hooks.emit": handle_scout_hook,
    "memory.get": handle_memory_get,
    "memory.put": handle_memory_put,
    "rag.search": handle_rag_search,
    "playbook.start": handle_playbook_start,
    "playbook.status": handle_playbook_status,
    "jobs.create": handle_jobs_create,
    "jobs.cancel": handle_jobs_cancel,
    "channels.notify": handle_channels_notify,
    "data.datasets.list": handle_data_datasets_list,
    "data.jobs.create": handle_data_jobs_create,
    "data.export": handle_data_export,
    "crm.enrich.licensed": handle_not_configured,
    "channels.whatsapp.send": handle_not_configured,
    "channels.sms.send": handle_not_configured,
    "social.oauth.publish": handle_not_configured,
    "ops.engine.probe": handle_ops_probe,
}


async def handle_pack_ping(ctx: RequestContext, payload: dict[str, Any]) -> dict[str, Any]:
    """Fixture-only node used by foundation isolation packs."""
    return {
        "ok": True,
        "product": ctx.product,
        "workspace_id": ctx.workspace_id,
        "message": str(payload.get("message") or "pong"),
        "correlation_id": ctx.correlation_id,
    }


HANDLERS["pack.ping"] = handle_pack_ping
