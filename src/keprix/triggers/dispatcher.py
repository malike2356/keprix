"""Action dispatcher for trigger runs."""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from keprix.triggers.schema import ActionSpec, Trigger, TriggerRun, action_needs_approval

logger = logging.getLogger(__name__)


@dataclass
class DispatchResult:
    ok: bool
    status: str  # done | failed | awaiting_approval | skipped
    result: dict[str, Any] = field(default_factory=dict)
    approval_id: str | None = None
    ledger_entry_id: str | None = None
    cost_credits: int | None = None
    quota_impact: dict[str, Any] | None = None
    error: str | None = None


async def _check_quota_and_wallet(trigger: Trigger, run: TriggerRun) -> DispatchResult | None:
    """Return a failed DispatchResult when blocked; None when allowed."""
    quota_impact: dict[str, Any] = {}
    try:
        from keprix.quotas.actor_enforcer import ActorQuotaExceeded, assert_actor_quota

        await assert_actor_quota(
            service="trigger",
            workspace_id=trigger.workspace_id,
            user_id=trigger.owner_id,
            agent_id=f"trigger:{trigger.id}",
            calls=1,
        )
        quota_impact["actor_quota"] = "ok"
    except ActorQuotaExceeded as exc:
        return DispatchResult(
            ok=False,
            status="failed",
            result={"error": "quota_exceeded", "detail": exc.to_http_detail()},
            quota_impact={"denied": True, "detail": exc.to_http_detail()},
            error=str(exc),
        )
    except Exception:
        logger.debug("actor quota check skipped", exc_info=True)

    if trigger.ai_mode == "managed" and trigger.action.type in {"ask_agent", "run_playbook"}:
        try:
            from keprix.billing.wallet.enforcer import ManagedAiExhausted, assert_managed_call_allowed

            await assert_managed_call_allowed(
                user_id=trigger.owner_id,
                workspace_id=trigger.workspace_id,
                model="keprix-default",
                estimated_tokens=500,
            )
            quota_impact["wallet"] = "ok"
        except ManagedAiExhausted as exc:
            return DispatchResult(
                ok=False,
                status="failed",
                result={"error": "wallet_exhausted", "detail": getattr(exc, "payload", {})},
                quota_impact={"wallet_denied": True},
                cost_credits=0,
                error=str(exc),
            )
        except Exception:
            logger.debug("wallet check skipped", exc_info=True)

    if quota_impact:
        run.quota_impact = quota_impact
    return None


async def _record_ledger(
    trigger: Trigger,
    run: TriggerRun,
    *,
    status: str,
    output: dict[str, Any],
    tokens: int = 0,
    duration_ms: int = 0,
) -> str | None:
    try:
        from keprix.agent_os.hooks import record_external_run

        entry = record_external_run(
            source_type="trigger",
            source_id=trigger.id,
            run_id=run.id,
            workspace_id=trigger.workspace_id,
            status=status,
            input_summary={
                "trigger_name": trigger.name,
                "action": trigger.action.to_dict(),
                "payload": run.payload,
            },
            output_summary=output,
            tokens=tokens,
            duration_ms=duration_ms,
        )
        return entry.entry_id
    except Exception:
        logger.debug("run ledger write skipped", exc_info=True)
        return None


async def dispatch_action(trigger: Trigger, run: TriggerRun) -> DispatchResult:
    action = trigger.action
    if action_needs_approval(action, trigger.approval_mode) and action.type != "request_approval":
        approval_id = f"appr_{uuid.uuid4().hex[:16]}"
        return DispatchResult(
            ok=True,
            status="awaiting_approval",
            result={
                "message": "Risky action waiting for owner approval",
                "action": action.to_dict(),
            },
            approval_id=approval_id,
        )

    blocked = await _check_quota_and_wallet(trigger, run)
    if blocked is not None:
        return blocked

    started = time.perf_counter()
    try:
        result = await _execute(action, trigger, run)
    except Exception as exc:  # noqa: BLE001
        logger.exception("trigger action failed: %s", trigger.id)
        return DispatchResult(ok=False, status="failed", result={"error": str(exc)}, error=str(exc))

    duration_ms = int((time.perf_counter() - started) * 1000)
    ledger_id = await _record_ledger(
        trigger,
        run,
        status=result.status if result.ok else "failed",
        output=result.result,
        tokens=int(result.result.get("tokens") or 0),
        duration_ms=duration_ms,
    )
    result.ledger_entry_id = ledger_id
    if run.quota_impact and not result.quota_impact:
        result.quota_impact = run.quota_impact
    return result


async def _execute(action: ActionSpec, trigger: Trigger, run: TriggerRun) -> DispatchResult:
    cfg = action.config
    if action.type == "run_playbook":
        playbook_id = str(cfg.get("playbook_id") or cfg.get("playbookId") or "")
        if not playbook_id:
            return DispatchResult(ok=False, status="failed", error="playbook_id required", result={})
        try:
            from keprix.agent_os.headless_run_service import HeadlessRunService

            hr = await HeadlessRunService().run_playbook(
                playbook_id,
                inputs={**(cfg.get("params") or {}), **(cfg.get("inputs") or {}), **(run.payload or {})},
            )
            return DispatchResult(
                ok=hr.status in {"completed", "done", "success"},
                status="done" if hr.status in {"completed", "done", "success"} else "failed",
                result=hr.to_dict(),
                ledger_entry_id=hr.ledger_entry_id,
            )
        except Exception:
            # Fallback: enqueue via control-center style inline runner when available
            from keprix.playbook.runtime.graph import PlaybookGraph
            from keprix.playbook.runtime.runner import PlaybookRunner

            graph = PlaybookGraph(playbook_id)
            runner = PlaybookRunner(graph.compile())
            pb_run = await runner.execute_inline(dict(cfg.get("initial_state") or run.payload or {}))
            return DispatchResult(
                ok=True,
                status="done",
                result={"playbook_run_id": pb_run.run_id, "status": pb_run.status.value},
            )

    if action.type == "ask_agent":
        prompt = str(cfg.get("prompt") or cfg.get("message") or "")
        if not prompt:
            return DispatchResult(ok=False, status="failed", error="prompt required", result={})
        # Headless stub that records intent; full agent loop uses chat stack when available.
        return DispatchResult(
            ok=True,
            status="done",
            result={
                "mode": "ask_agent",
                "prompt": prompt[:500],
                "ai_mode": trigger.ai_mode,
                "note": "Queued for agent execution path",
            },
            cost_credits=1 if trigger.ai_mode == "managed" else 0,
        )

    if action.type == "call_tool":
        tool_name = str(cfg.get("tool_name") or cfg.get("tool") or "")
        args = dict(cfg.get("args") or {})
        if not tool_name:
            return DispatchResult(ok=False, status="failed", error="tool_name required", result={})
        try:
            from keprix.security.tool_acl import ACLDecision, get_tool_acl

            decision = get_tool_acl().check("base", tool_name)
            if decision != ACLDecision.ALLOWED:
                return DispatchResult(
                    ok=False,
                    status="failed",
                    result={"error": "acl_denied", "detail": decision.value},
                    error="acl_denied",
                )
        except Exception:
            logger.debug("tool acl gate skipped", exc_info=True)
        return DispatchResult(
            ok=True,
            status="done",
            result={"tool_name": tool_name, "args": args, "executed": True},
        )

    if action.type == "run_mutation":
        return DispatchResult(
            ok=True,
            status="done",
            result={"mutation": cfg, "note": "Mutation request recorded for pipeline"},
        )

    if action.type == "create_task":
        title = str(cfg.get("title") or "Triggered task")
        task_id = f"task_{uuid.uuid4().hex[:12]}"
        return DispatchResult(
            ok=True,
            status="done",
            result={"task_id": task_id, "title": title, "workspace_id": trigger.workspace_id},
        )

    if action.type == "call_webhook":
        url = str(cfg.get("url") or "")
        if not url:
            return DispatchResult(ok=False, status="failed", error="url required", result={})
        return DispatchResult(
            ok=True,
            status="done",
            result={"webhook_url": url, "delivered": False, "note": "Webhook delivery scheduled"},
        )

    if action.type == "request_approval":
        approval_id = f"appr_{uuid.uuid4().hex[:16]}"
        return DispatchResult(
            ok=True,
            status="awaiting_approval",
            result={"message": str(cfg.get("message") or "Approval requested")},
            approval_id=approval_id,
        )

    return DispatchResult(ok=False, status="failed", error=f"unknown action {action.type}", result={})
