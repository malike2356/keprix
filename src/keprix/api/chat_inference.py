"""Web chat LLM inference for the conversation workspace API."""

from __future__ import annotations

import asyncio
import os
import time
from typing import Any, AsyncIterator

from keprix.api.codebase_context import build_codebase_system_prompt, redact_assistant_text

PROVIDER_DEFAULT_MODELS: dict[str, str] = {
    "deepseek": "deepseek-chat",
    "openai": "gpt-4.1-mini",
    "anthropic": "claude-sonnet-4-6",
    "gemini": "gemini-2.5-pro",
    "google": "gemini-2.5-pro",
    "groq": "llama-3.3-70b",
    "xai": "grok-2-latest",
    "openrouter": "openrouter/auto",
    "ollama": "llama3.2",
}

WEB_CHAT_PROVIDERS: tuple[str, ...] = (
    "deepseek",
    "openai",
    "anthropic",
    "google",
    "groq",
    "xai",
    "openrouter",
    "ollama",
)

# ---------------------------------------------------------------------------
# Provider configuration cache
# Re-checked at most once per TTL so registry I/O is not on the hot path.
# Call invalidate_provider_cache() after the user saves a new API key.
# ---------------------------------------------------------------------------

_PROVIDER_CACHE_TTL = 60.0
_provider_status_cache: dict[str, tuple[bool, float]] = {}
_default_provider_result: tuple[str, str] | None = None
_default_provider_ts: float = 0.0


def _provider_configured(provider_id: str) -> bool:
    from keprix.api.provider_settings import registry_provider_id

    now = time.monotonic()
    cached = _provider_status_cache.get(provider_id)
    if cached is not None and now - cached[1] < _PROVIDER_CACHE_TTL:
        return cached[0]

    try:
        from keprix_cli.auth import get_api_key_provider_status

        registry_id = registry_provider_id(provider_id)
        result = bool(get_api_key_provider_status(registry_id).get("configured"))
    except Exception:
        result = False

    _provider_status_cache[provider_id] = (result, now)
    return result


def invalidate_provider_cache() -> None:
    """Call after the user saves or removes an API key."""
    global _default_provider_result, _default_provider_ts
    _provider_status_cache.clear()
    _default_provider_result = None
    _default_provider_ts = 0.0


def resolve_default_provider_model() -> tuple[str, str]:
    global _default_provider_result, _default_provider_ts
    now = time.monotonic()
    if _default_provider_result is not None and now - _default_provider_ts < _PROVIDER_CACHE_TTL:
        return _default_provider_result

    preferred = os.getenv("KEPRIX_DEFAULT_PROVIDER", "").strip().lower()
    if preferred and _provider_configured(preferred):
        result: tuple[str, str] = (preferred, PROVIDER_DEFAULT_MODELS.get(preferred, "default"))
    else:
        result = next(
            (
                (p, PROVIDER_DEFAULT_MODELS.get(p, "default"))
                for p in WEB_CHAT_PROVIDERS
                if _provider_configured(p)
            ),
            ("deepseek", PROVIDER_DEFAULT_MODELS["deepseek"]),
        )

    _default_provider_result = result
    _default_provider_ts = now
    return result


def parse_model_id(model_id: str | None) -> tuple[str, str]:
    if not model_id:
        return resolve_default_provider_model()
    if ":" in model_id:
        provider, model = model_id.split(":", 1)
        provider = provider.strip().lower()
        model = model.strip()
        if not _provider_configured(provider):
            return resolve_default_provider_model()
        if model:
            return provider, model
        return provider, PROVIDER_DEFAULT_MODELS.get(provider, "default")
    provider, default_model = resolve_default_provider_model()
    return provider, model_id.strip() or default_model


def list_available_models() -> list[dict[str, str]]:
    models: list[dict[str, str]] = []
    default_provider, _ = resolve_default_provider_model()
    for provider in WEB_CHAT_PROVIDERS:
        if not _provider_configured(provider):
            continue
        model_name = PROVIDER_DEFAULT_MODELS.get(provider, "default")
        models.append(
            {
                "id": f"{provider}:{model_name}",
                "provider": provider,
                "name": model_name,
            }
        )
    if not models:
        provider, model_name = resolve_default_provider_model()
        models.append(
            {
                "id": f"{provider}:{model_name}",
                "provider": provider,
                "name": model_name,
            }
        )
    models.sort(key=lambda item: (item["provider"] != default_provider, item["provider"]))
    return models


def _normalize_history(messages: list[dict[str, Any]]) -> list[dict[str, str]]:
    normalized: list[dict[str, str]] = []
    for message in messages:
        role = str(message.get("role") or "").strip().lower()
        if role not in {"user", "assistant", "system"}:
            continue
        content = message.get("content")
        text = ""
        if isinstance(content, str):
            text = content.strip()
        elif isinstance(content, list):
            parts: list[str] = []
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    parts.append(str(block.get("content") or "").strip())
            text = "\n".join(part for part in parts if part)
        if text:
            normalized.append({"role": role, "content": text})
    return normalized


def _registry_provider_id(provider: str) -> str:
    if provider == "google":
        return "gemini"
    if provider == "openai":
        return "openai-api"
    return provider


def _extract_delta_text(chunk: Any) -> str | None:
    choices = getattr(chunk, "choices", None) or []
    if not choices:
        return None
    delta = getattr(choices[0], "delta", None)
    text = getattr(delta, "content", None) if delta is not None else None
    return str(text) if text else None


async def _stream_via_thread(client: Any, resolved_model: str, messages: list[dict[str, str]]) -> AsyncIterator[str]:
    """
    Thread-based streaming path for clients that do not support native
    async iteration (Anthropic shim, custom adapters).

    Uses asyncio.Queue + call_soon_threadsafe so the async loop is woken
    immediately when each token arrives - no polling timeout.
    """
    q: asyncio.Queue[str | None] = asyncio.Queue()
    loop = asyncio.get_running_loop()
    exc_holder: list[Exception] = []

    def _producer() -> None:
        try:
            stream = client.chat.completions.create(
                model=resolved_model,
                messages=messages,
                stream=True,
            )
            for chunk in stream:
                text = _extract_delta_text(chunk)
                if text:
                    loop.call_soon_threadsafe(q.put_nowait, text)
        except Exception as exc:
            exc_holder.append(exc)
        finally:
            loop.call_soon_threadsafe(q.put_nowait, None)

    worker = loop.run_in_executor(None, _producer)

    while True:
        item = await q.get()
        if item is None:
            break
        yield redact_assistant_text(item)

    await worker
    if exc_holder:
        raise exc_holder[0]


async def stream_chat_completion(
    *,
    user_text: str,
    model_id: str | None,
    history: list[dict[str, Any]] | None = None,
) -> AsyncIterator[str]:
    provider, model = parse_model_id(model_id)
    if not _provider_configured(provider):
        raise RuntimeError(
            f"Provider '{provider}' is not configured. Add its API key to .env and restart the backend."
        )

    messages = _normalize_history(history or [])
    system_prompt = build_codebase_system_prompt()
    if system_prompt:
        messages.insert(0, {"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": user_text})

    from agent.auxiliary_client import resolve_provider_client

    registry_provider = _registry_provider_id(provider)
    client, resolved_model = resolve_provider_client(registry_provider, model, async_mode=True)
    if client is None:
        raise RuntimeError(f"Provider '{provider}' is not configured")

    # Native async path: AsyncOpenAI (and compatible: Groq, DeepSeek, xAI).
    # Streams directly via httpx; no thread, no polling, first token arrives
    # as soon as the network delivers it.
    try:
        from openai import AsyncOpenAI as _AsyncOpenAI

        if isinstance(client, _AsyncOpenAI):
            async with await client.chat.completions.create(
                model=resolved_model,
                messages=messages,
                stream=True,
            ) as stream:
                async for chunk in stream:
                    text = _extract_delta_text(chunk)
                    if text:
                        yield redact_assistant_text(text)
            return
    except ImportError:
        pass

    # Fallback: thread-based streaming with zero-delay asyncio.Queue handoff.
    async for token in _stream_via_thread(client, resolved_model, messages):
        yield token
