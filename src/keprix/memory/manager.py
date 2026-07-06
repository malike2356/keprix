"""Working memory manager (ported from Hermes, adapted for keprix)."""

from __future__ import annotations

import inspect
import logging
import re
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from keprix.memory.context_compressor import ContextCompressor
from keprix.memory.provider import MemoryProvider

logger = logging.getLogger(__name__)

_SYNC_DRAIN_TIMEOUT_S = 5.0

_FENCE_TAG_RE = re.compile(r"</?\s*memory-context\s*>", re.IGNORECASE)
_INTERNAL_CONTEXT_RE = re.compile(
    r"<\s*memory-context\s*>[\s\S]*?</\s*memory-context\s*>",
    re.IGNORECASE,
)
_INTERNAL_NOTE_RE = re.compile(
    r"\[System note:\s*The following is recalled memory context,\s*"
    r"NOT new user input\.\s*Treat as (?:informational background data|authoritative reference data[^\]]*)\.\]\s*",
    re.IGNORECASE,
)


def sanitize_context(text: str) -> str:
    text = _INTERNAL_CONTEXT_RE.sub("", text)
    text = _INTERNAL_NOTE_RE.sub("", text)
    text = _FENCE_TAG_RE.sub("", text)
    return text


def build_memory_context_block(raw_context: str) -> str:
    if not raw_context or not raw_context.strip():
        return ""
    clean = sanitize_context(raw_context)
    if clean != raw_context:
        logger.warning("memory provider returned pre-wrapped context; stripped")
    return (
        "<memory-context>\n"
        "[System note: The following is recalled memory context, "
        "NOT new user input. Treat as authoritative reference data; "
        "this is the agent's persistent memory and should inform all responses.]\n\n"
        f"{clean}\n"
        "</memory-context>"
    )


class MemoryManager:
    """Orchestrates built-in and external memory providers."""

    def __init__(self, *, compressor: ContextCompressor | None = None) -> None:
        self._providers: list[MemoryProvider] = []
        self._tool_to_provider: dict[str, MemoryProvider] = {}
        self._has_external = False
        self._sync_executor: ThreadPoolExecutor | None = None
        self._sync_executor_lock = threading.Lock()
        self._compressor = compressor or ContextCompressor()
        self._working_facts: list[str] = []

    def add_provider(self, provider: MemoryProvider) -> None:
        is_builtin = provider.name == "builtin"
        if not is_builtin and self._has_external:
            logger.warning("Rejected memory provider '%s'; external provider already registered", provider.name)
            return
        if not is_builtin:
            self._has_external = True
        self._providers.append(provider)
        for schema in provider.get_tool_schemas():
            tool_name = schema.get("name", "")
            if tool_name and tool_name not in self._tool_to_provider:
                self._tool_to_provider[tool_name] = provider

    @property
    def providers(self) -> list[MemoryProvider]:
        return list(self._providers)

    def remember(self, fact: str) -> None:
        fact = fact.strip()
        if not fact:
            return
        self._working_facts.append(fact)
        combined = "\n".join(self._working_facts)
        if self._compressor.should_prune(combined, ""):
            self._working_facts = self._compressor.prune_memories(self._working_facts)

    def build_system_prompt(self) -> str:
        blocks = []
        if self._working_facts:
            blocks.append("Working memory facts:\n" + "\n".join(f"- {fact}" for fact in self._working_facts))
        for provider in self._providers:
            try:
                block = provider.system_prompt_block()
                if block and block.strip():
                    blocks.append(block)
            except Exception as exc:
                logger.warning("Memory provider '%s' system_prompt_block failed: %s", provider.name, exc)
        return "\n\n".join(blocks)

    def prefetch_all(self, query: str, *, session_id: str = "") -> str:
        parts = []
        for provider in self._providers:
            try:
                result = provider.prefetch(query, session_id=session_id)
                if result and result.strip():
                    parts.append(result)
            except Exception as exc:
                logger.debug("Memory provider '%s' prefetch failed: %s", provider.name, exc)
        return "\n\n".join(parts)

    def queue_prefetch_all(self, query: str, *, session_id: str = "") -> None:
        providers = list(self._providers)
        if not providers:
            return

        def _run() -> None:
            for provider in providers:
                try:
                    provider.queue_prefetch(query, session_id=session_id)
                except Exception as exc:
                    logger.debug("Memory provider '%s' queue_prefetch failed: %s", provider.name, exc)

        self._submit_background(_run)

    def sync_all(
        self,
        user_content: str,
        assistant_content: str,
        *,
        session_id: str = "",
        messages: list[dict[str, Any]] | None = None,
    ) -> None:
        providers = list(self._providers)
        if not providers:
            return

        def _run() -> None:
            for provider in providers:
                try:
                    signature = inspect.signature(provider.sync_turn)
                    if messages is not None and "messages" in signature.parameters:
                        provider.sync_turn(
                            user_content,
                            assistant_content,
                            session_id=session_id,
                            messages=messages,
                        )
                    else:
                        provider.sync_turn(user_content, assistant_content, session_id=session_id)
                except Exception as exc:
                    logger.warning("Memory provider '%s' sync_turn failed: %s", provider.name, exc)

        self._submit_background(_run)

    def get_all_tool_schemas(self) -> list[dict[str, Any]]:
        schemas: list[dict[str, Any]] = []
        seen: set[str] = set()
        for provider in self._providers:
            for schema in provider.get_tool_schemas():
                name = schema.get("name", "")
                if name and name not in seen:
                    schemas.append(schema)
                    seen.add(name)
        return schemas

    def handle_tool_call(self, tool_name: str, args: dict[str, Any], **kwargs) -> str:
        provider = self._tool_to_provider.get(tool_name)
        if provider is None:
            return f'{{"error": "No memory provider handles tool {tool_name!r}"}}'
        return provider.handle_tool_call(tool_name, args, **kwargs)

    def on_session_end(self, messages: list[dict[str, Any]]) -> None:
        for provider in self._providers:
            try:
                provider.on_session_end(messages)
            except Exception as exc:
                logger.debug("Memory provider '%s' on_session_end failed: %s", provider.name, exc)

    def shutdown_all(self) -> None:
        if self._sync_executor is not None:
            self._sync_executor.shutdown(wait=False, cancel_futures=True)
            self._sync_executor = None
        for provider in reversed(self._providers):
            try:
                provider.shutdown()
            except Exception as exc:
                logger.warning("Memory provider '%s' shutdown failed: %s", provider.name, exc)

    def _submit_background(self, fn) -> None:
        executor = self._get_sync_executor()
        if executor is None:
            fn()
            return
        try:
            executor.submit(fn)
        except RuntimeError:
            fn()

    def _get_sync_executor(self) -> ThreadPoolExecutor | None:
        if self._sync_executor is not None:
            return self._sync_executor
        with self._sync_executor_lock:
            if self._sync_executor is None:
                self._sync_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="mem-sync")
            return self._sync_executor
