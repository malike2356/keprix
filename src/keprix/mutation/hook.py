"""Gap-to-synthesis pipeline hooks (Prompt 151)."""

from __future__ import annotations

import asyncio
import logging
import threading
from typing import Any

from keprix.improvement.run_analyzer import ImprovementProposal, RunRecord
from keprix.improvement.tool_gap_detector import ToolGapProposal, detect_tool_gaps
from keprix.mutation.config import get_mutation_settings
from keprix.mutation.store import MutationStore, get_mutation_store
from keprix.mutation.tool_synthesizer import synthesize_tool

from keprix.agent.keprix.mutation_dispatch import finalize_sync_tool_miss, run_tool_miss_cycle

logger = logging.getLogger(__name__)

_synthesis_locks: dict[str, threading.Lock] = {}
_locks_guard = threading.Lock()


def _get_synthesis_lock(tool_name: str) -> threading.Lock:
    with _locks_guard:
        lock = _synthesis_locks.get(tool_name)
        if lock is None:
            lock = threading.Lock()
            _synthesis_locks[tool_name] = lock
        return lock


def _tool_in_registry(tool_name: str) -> bool:
    try:
        from tools.registry import registry

        return registry.get_tool(tool_name) is not None
    except Exception:
        return False


def _generated_tool_record(tool_name: str):
    try:
        from keprix.agent.keprix.store import get_generated_tool_store

        normalized = tool_name.strip().lower()
        for record in get_generated_tool_store().list_all():
            if record.tool_name.strip().lower() == normalized:
                return record
    except Exception:
        return None
    return None


def _record_synthesis_usage(tool_name: str, tokens_used: int, run_id: str) -> None:
    if tokens_used <= 0:
        return
    try:
        from keprix.usage.recorder import get_llm_usage_recorder

        asyncio.get_event_loop().create_task(
            get_llm_usage_recorder().record(
                usage={"total_tokens": tokens_used},
                provider="mutation",
                model="mutation_tool_synthesis",
                channel="mutation",
                metadata={"tool_name": tool_name, "run_id": run_id},
            )
        )
    except RuntimeError:
        try:
            asyncio.run(
                get_llm_usage_recorder().record(
                    usage={"total_tokens": tokens_used},
                    provider="mutation",
                    model="mutation_tool_synthesis",
                    channel="mutation",
                    metadata={"tool_name": tool_name, "run_id": run_id},
                )
            )
        except Exception:
            pass
    except Exception as exc:
        logger.debug("mutation usage record skipped: %s", exc)


def _hot_load_approved_record(store: MutationStore, record) -> None:
    if record.status != "approved" or not record.source_code:
        return
    generated_dir = store.generated_tools_dir()
    store.write_tool_to_disk(record, generated_dir)
    store.reload_registry(generated_dir)


async def on_tool_miss(
    tool_name: str,
    task_context: str,
    run_id: str,
    workspace_id: str,
    store: MutationStore,
) -> str | None:
    """Synthesize a missing tool on demand. Never raises."""
    settings = get_mutation_settings()
    if not settings.enabled or not settings.tool_synthesis:
        return None

    normalized = tool_name.strip()
    lock = _get_synthesis_lock(normalized.lower())

    try:
        with lock:
            if _tool_in_registry(normalized):
                return None

            existing = store.find_generated_by_name(workspace_id, normalized)
            if existing is not None:
                if existing.status == "approved":
                    _hot_load_approved_record(store, existing)
                    return (
                        f"Tool '{normalized}' was not found. A replacement was synthesized "
                        "and is now available. Retry the task."
                    )
                return (
                    f"Tool '{normalized}' is not available. A synthesis is staged and "
                    "awaiting operator approval."
                )

            generated = _generated_tool_record(normalized)
            if generated is not None:
                if generated.status in {"installed", "approved"}:
                    return (
                        f"Tool '{normalized}' was not found. A replacement was synthesized "
                        "and is now available. Retry the task."
                    )
                return (
                    f"Tool '{normalized}' is not available. A synthesis is staged and "
                    "awaiting operator approval."
                )

            result = await run_tool_miss_cycle(
                task=task_context or f"Missing tool: {normalized}",
                requested_tool=normalized,
                session_id=run_id or None,
            )
            return await finalize_sync_tool_miss(
                result,
                tool_name=normalized,
                confidence=1.0,
            )
    except Exception as exc:
        logger.exception("on_tool_miss failed for %s: %s", tool_name, exc)
        return (
            f"Tool '{tool_name}' was not found and synthesis encountered an error. "
            "Use an available tool or rephrase the task."
        )


async def on_run_complete(
    record: RunRecord,
    proposals: list[ImprovementProposal],
    workspace_id: str,
    store: MutationStore,
) -> list[str]:
    """Background synthesis for tool gaps detected after a run completes."""
    settings = get_mutation_settings()
    if not settings.enabled or not settings.tool_synthesis:
        return []

    synthesized: list[str] = []
    gaps = detect_tool_gaps(record, proposals)
    for gap in gaps:
        if gap.confidence < settings.synthesis_min_confidence:
            continue
        if _tool_in_registry(gap.tool_name):
            continue
        if store.find_generated_by_name(workspace_id, gap.tool_name) is not None:
            continue
        name = await _synthesize_gap_background(gap, workspace_id, store, record.run_id)
        if name:
            synthesized.append(name)
    return synthesized


async def _synthesize_gap_background(
    gap: ToolGapProposal,
    workspace_id: str,
    store: MutationStore,
    run_id: str,
) -> str | None:
    lock = _get_synthesis_lock(gap.tool_name.lower())
    settings = get_mutation_settings()
    try:
        with lock:
            if _tool_in_registry(gap.tool_name):
                return None
            if store.find_generated_by_name(workspace_id, gap.tool_name) is not None:
                return None
            result = await synthesize_tool(gap, workspace_id)
            _record_synthesis_usage(result.tool_name, result.tokens_used, run_id)
            if not result.success or not result.source_code:
                logger.warning(
                    "background synthesis failed for %s: %s",
                    gap.tool_name,
                    result.error,
                )
                return None
            saved = store.save_generated_tool(
                workspace_id=workspace_id,
                tool_name=result.tool_name,
                description=gap.description,
                source_code=result.source_code,
                trigger="gap_detected",
                confidence=gap.confidence,
                auto_approve_threshold=settings.auto_approve_threshold,
            )
            if saved.status == "approved":
                _hot_load_approved_record(store, saved)
            return saved.name
    except Exception as exc:
        logger.exception("background synthesis failed for %s: %s", gap.tool_name, exc)
        return None


def schedule_on_run_complete(
    record: RunRecord,
    proposals: list[ImprovementProposal],
    workspace_id: str,
    store: MutationStore | None = None,
) -> None:
    """Fire-and-forget wrapper for improvement routes."""
    settings = get_mutation_settings()
    if not settings.enabled or not settings.tool_synthesis:
        return
    mutation_store = store or get_mutation_store()

    async def _runner() -> None:
        await on_run_complete(record, proposals, workspace_id, mutation_store)

    try:
        asyncio.create_task(_runner())
    except RuntimeError:
        logger.debug("no event loop for on_run_complete; skipping background synthesis")


def install_tool_miss_hook_on_agent(agent: Any) -> None:
    """Attach sync tool-miss hook used by conversation_loop."""
    settings = get_mutation_settings()
    if not settings.enabled or not settings.tool_synthesis:
        return

    def _sync_hook(invalid_name: str, user_message: str, bound_agent: Any) -> str | None:
        workspace_id = getattr(bound_agent, "_gateway_session_key", None) or "default"
        run_id = getattr(bound_agent, "session_id", None) or ""
        task_context = user_message or ""
        try:
            return asyncio.run(
                on_tool_miss(
                    tool_name=invalid_name,
                    task_context=task_context,
                    run_id=run_id,
                    workspace_id=workspace_id,
                    store=get_mutation_store(),
                )
            )
        except Exception as exc:
            logger.debug("sync tool miss hook failed: %s", exc)
            return None

    agent._keprix_on_tool_miss = _sync_hook
