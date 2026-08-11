"""Web chat LLM inference for the conversation workspace API."""

from __future__ import annotations

import asyncio
import os
import time
from dataclasses import dataclass
from typing import Any, AsyncIterator

from keprix.api.codebase_context import build_codebase_system_prompt, redact_assistant_text
from keprix.memory.rag.self_knowledge import format_self_knowledge_context, retrieve_self_knowledge

PROVIDER_DEFAULT_MODELS: dict[str, str] = {
    "deepseek": "deepseek-v4-pro",
    "openai": "gpt-4.1-mini",
    "anthropic": "claude-sonnet-4-6",
    "gemini": "gemini-2.5-pro",
    "google": "gemini-2.5-pro",
    "groq": "llama-3.3-70b",
    "xai": "grok-2-latest",
    "openrouter": "openrouter/auto",
    "ollama": "llama3.2",
}

CUSTOM_PREFIX = "custom/"


def _custom_provider_public_key(provider_id: str) -> str:
    return f"{CUSTOM_PREFIX}{provider_id}"


def _load_custom_provider_entry(provider_id: str) -> dict[str, Any] | None:
    try:
        from keprix.api.custom_provider_settings import get_custom_provider_raw

        return get_custom_provider_raw(provider_id)
    except Exception:
        return None


def _custom_provider_configured(provider_id: str) -> bool:
    entry = _load_custom_provider_entry(provider_id)
    if entry is None:
        return False
    base_url = str(entry.get("base_url") or "").strip()
    if not base_url:
        return False
    api_key = str(entry.get("api_key") or "").strip()
    key_env = str(entry.get("key_env") or "").strip()
    if api_key or (key_env and os.getenv(key_env, "").strip()):
        return True
    host = base_url.replace("https://", "").replace("http://", "").split("/")[0]
    return host.startswith("localhost") or host.startswith("127.0.0.1")


def _list_custom_models() -> list[dict[str, str]]:
    try:
        from keprix.api.custom_provider_settings import list_custom_providers

        providers = list_custom_providers()
    except Exception:
        # Config home may be unreadable in Docker (host uid mount vs container user).
        # Never fail the models list endpoint for custom-provider discovery.
        return []

    models: list[dict[str, str]] = []
    for provider in providers:
        if not provider.get("connected"):
            continue
        provider_id = str(provider["id"])
        model_name = str(provider.get("default_model") or "default")
        public_key = _custom_provider_public_key(provider_id)
        models.append(
            {
                "id": f"{public_key}:{model_name}",
                "provider": public_key,
                "name": model_name,
                "label": str(provider.get("name") or provider_id),
            }
        )
    return models


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
    if provider_id.startswith(CUSTOM_PREFIX):
        return _custom_provider_configured(provider_id.removeprefix(CUSTOM_PREFIX))

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


def _resolve_custom_provider_model(provider_id: str, model: str | None = None) -> tuple[str, str] | None:
    entry = _load_custom_provider_entry(provider_id)
    if entry is None:
        return None
    resolved_model = (model or str(entry.get("model") or "")).strip() or "default"
    return _custom_provider_public_key(provider_id), resolved_model


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
    if preferred.startswith(CUSTOM_PREFIX):
        custom_id = preferred.removeprefix(CUSTOM_PREFIX)
        if _custom_provider_configured(custom_id):
            entry = _load_custom_provider_entry(custom_id)
            model = str((entry or {}).get("model") or "default")
            result = (preferred, model)
            _default_provider_result = result
            _default_provider_ts = now
            return result
    if preferred and _provider_configured(preferred):
        result = (preferred, PROVIDER_DEFAULT_MODELS.get(preferred, "default"))
    else:
        custom_models = _list_custom_models()
        if custom_models:
            first = custom_models[0]
            result = (str(first["provider"]), str(first["name"]))
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
        if provider.startswith(CUSTOM_PREFIX):
            custom_id = provider.removeprefix(CUSTOM_PREFIX)
            if _custom_provider_configured(custom_id):
                resolved = _resolve_custom_provider_model(custom_id, model or None)
                if resolved is not None:
                    return resolved
            return resolve_default_provider_model()
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
    models.extend(_list_custom_models())
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


def _estimate_message_tokens(messages: list[dict[str, str]]) -> int:
    chars = sum(len(str(message.get("content") or "")) for message in messages)
    return max(1, chars // 4)


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


def _extract_chunk_usage(chunk: Any) -> dict[str, int] | None:
    usage = getattr(chunk, "usage", None)
    if usage is None:
        return None
    if isinstance(usage, dict):
        raw = usage
    else:
        raw = {
            "input_tokens": getattr(usage, "prompt_tokens", None) or getattr(usage, "input_tokens", 0),
            "output_tokens": getattr(usage, "completion_tokens", None) or getattr(usage, "output_tokens", 0),
            "total_tokens": getattr(usage, "total_tokens", 0),
            "cache_read_tokens": getattr(usage, "cache_read_input_tokens", None)
            or getattr(usage, "cache_read_tokens", 0),
            "cache_write_tokens": getattr(usage, "cache_creation_input_tokens", None)
            or getattr(usage, "cache_write_tokens", 0),
            "reasoning_tokens": getattr(usage, "reasoning_tokens", 0),
        }
    from agent.usage_pricing import normalize_usage

    canonical = normalize_usage(raw)
    return {
        "input_tokens": canonical.input_tokens,
        "output_tokens": canonical.output_tokens,
        "cache_read_tokens": canonical.cache_read_tokens,
        "cache_write_tokens": canonical.cache_write_tokens,
        "reasoning_tokens": canonical.reasoning_tokens,
        "total_tokens": canonical.total_tokens,
    }


async def _record_web_chat_usage(
    *,
    provider: str,
    model: str,
    usage_counts: dict[str, int] | None,
    user_id: str | None,
    session_id: str | None,
    duration_ms: int | None = None,
    note: str | None = None,
    channel: str = "web_ui",
) -> None:
    from keprix.usage.pricing_bridge import usage_from_counts
    from keprix.usage.recorder import get_llm_usage_recorder

    if usage_counts:
        usage = usage_from_counts(
            input_tokens=usage_counts.get("input_tokens", 0),
            output_tokens=usage_counts.get("output_tokens", 0),
            cache_read_tokens=usage_counts.get("cache_read_tokens", 0),
            cache_write_tokens=usage_counts.get("cache_write_tokens", 0),
            reasoning_tokens=usage_counts.get("reasoning_tokens", 0),
        )
        metadata = {}
    else:
        usage = usage_from_counts()
        metadata = {"usage_note": note or "provider omitted stream usage metadata"}

    await get_llm_usage_recorder().record(
        usage=usage,
        provider=provider,
        model=model,
        channel=channel,
        user_id=user_id,
        session_id=session_id,
        duration_ms=duration_ms,
        metadata=metadata,
    )


async def _stream_via_thread(
    client: Any,
    resolved_model: str,
    messages: list[dict[str, str]],
    usage_holder: dict[str, int] | None,
) -> AsyncIterator[str]:
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
                stream_options={"include_usage": True},
            )
            for chunk in stream:
                if usage_holder is not None:
                    parsed = _extract_chunk_usage(chunk)
                    if parsed:
                        usage_holder.update(parsed)
                text = _extract_delta_text(chunk)
                if text:
                    loop.call_soon_threadsafe(q.put_nowait, text)
        except TypeError:
            stream = client.chat.completions.create(
                model=resolved_model,
                messages=messages,
                stream=True,
            )
            for chunk in stream:
                if usage_holder is not None:
                    parsed = _extract_chunk_usage(chunk)
                    if parsed:
                        usage_holder.update(parsed)
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
    user_id: str | None = None,
    session_id: str | None = None,
    channel: str = "web_ui",
    include_codebase_context: bool = True,
) -> AsyncIterator[str]:
    started = time.perf_counter()
    from keprix.transparency.pipeline import prepare_ai_call

    prepare_ai_call(user_id, "text_generation")
    provider, model = parse_model_id(model_id)
    if not _provider_configured(provider):
        raise RuntimeError(
            f"Provider '{provider}' is not configured. Add its API key to .env and restart the backend."
        )

    messages = _normalize_history(history or [])
    onboarding_suffix = ""
    try:
        from keprix.agent.onboarding_hooks import first_message_system_suffix

        onboarding_suffix = first_message_system_suffix(history=history)
    except Exception:
        onboarding_suffix = ""
    if include_codebase_context:
        system_prompt = build_codebase_system_prompt()
        try:
            rag_hits = await retrieve_self_knowledge(user_text, limit=6, hybrid=True)
            rag_block = format_self_knowledge_context(rag_hits, max_chars=5_500)
            if rag_block:
                system_prompt = f"{system_prompt}\n\n{rag_block}" if system_prompt else rag_block
        except Exception:
            pass
        if onboarding_suffix:
            system_prompt = f"{system_prompt}{onboarding_suffix}" if system_prompt else onboarding_suffix.lstrip()
        if system_prompt:
            messages.insert(0, {"role": "system", "content": system_prompt})
    elif onboarding_suffix:
        messages.insert(0, {"role": "system", "content": onboarding_suffix.lstrip()})
    messages.append({"role": "user", "content": user_text})

    usage_holder: dict[str, int] = {}
    resolved_model = model
    output_chars = 0
    output_parts: list[str] = []
    quota_product_id = "keprix"
    scheduler_token = None
    estimated_input_tokens = _estimate_message_tokens(messages)
    quota_recordable = False

    try:
        try:
            from keprix.security.product_context import get_product_context_or_none

            ctx = get_product_context_or_none()
            if ctx is not None:
                quota_product_id = ctx.product_id
        except Exception:
            quota_product_id = "keprix"

        try:
            from keprix.quotas.runtime import get_fairness_scheduler, get_quota_enforcer

            quota_result = await get_quota_enforcer().check_before_llm_call(quota_product_id, estimated_input_tokens)
            if quota_result.warning_message:
                messages.insert(0, {"role": "system", "content": quota_result.warning_message})
            if quota_result.is_hard_blocked:
                raise RuntimeError(f"Quota blocked LLM call for product '{quota_product_id}': {quota_result.reason}")
            scheduler_token = await get_fairness_scheduler().acquire_slot(quota_product_id)
            quota_recordable = True
        except RuntimeError:
            raise
        except Exception:
            scheduler_token = None

        # Actor-scoped day/month quotas (workspace/user/agent/token). Separate from billing credits.
        try:
            from keprix.quotas.actor_enforcer import ActorQuotaExceeded, assert_actor_quota

            await assert_actor_quota(
                service="llm",
                workspace_id=None,
                user_id=user_id,
                product_id=quota_product_id,
                tokens=estimated_input_tokens,
                calls=1,
                run_id=session_id,
            )
        except ActorQuotaExceeded:
            raise
        except Exception:
            pass

        # Managed AI wallet gate (hosted only). BYOK and self-hosted skip debit.
        user_supplied_key = provider.startswith(CUSTOM_PREFIX)
        try:
            from keprix.billing.wallet.enforcer import ManagedAiExhausted, assert_managed_call_allowed

            await assert_managed_call_allowed(
                user_id=user_id,
                model=model,
                estimated_tokens=estimated_input_tokens,
                user_supplied_api_key=user_supplied_key,
            )
        except ManagedAiExhausted:
            raise
        except Exception:
            pass

        if provider.startswith(CUSTOM_PREFIX):
            custom_id = provider.removeprefix(CUSTOM_PREFIX)
            entry = _load_custom_provider_entry(custom_id)
            if entry is None:
                raise RuntimeError(f"Custom provider '{custom_id}' was not found")
            base_url = str(entry.get("base_url") or "").strip().rstrip("/")
            api_key = str(entry.get("api_key") or os.getenv(str(entry.get("key_env") or ""), "")).strip() or "no-key"
            resolved_model = model or str(entry.get("model") or "default")
            try:
                from openai import AsyncOpenAI

                client = AsyncOpenAI(api_key=api_key, base_url=base_url)
                try:
                    stream_ctx = await client.chat.completions.create(
                        model=resolved_model,
                        messages=messages,
                        stream=True,
                        stream_options={"include_usage": True},
                    )
                except TypeError:
                    stream_ctx = await client.chat.completions.create(
                        model=resolved_model,
                        messages=messages,
                        stream=True,
                    )
                async with stream_ctx as stream:
                    async for chunk in stream:
                        parsed = _extract_chunk_usage(chunk)
                        if parsed:
                            usage_holder.update(parsed)
                        text = _extract_delta_text(chunk)
                        if text:
                            redacted = redact_assistant_text(text)
                            output_chars += len(redacted)
                            output_parts.append(redacted)
                            yield redacted
            except ImportError as exc:
                raise RuntimeError("OpenAI client is required for custom providers") from exc
        else:
            from agent.auxiliary_client import resolve_provider_client

            registry_provider = _registry_provider_id(provider)
            client, resolved_model = resolve_provider_client(registry_provider, model, async_mode=True)
            if client is None:
                raise RuntimeError(f"Provider '{provider}' is not configured")

            try:
                from openai import AsyncOpenAI as _AsyncOpenAI

                if isinstance(client, _AsyncOpenAI):
                    try:
                        stream_ctx = await client.chat.completions.create(
                            model=resolved_model,
                            messages=messages,
                            stream=True,
                            stream_options={"include_usage": True},
                        )
                    except TypeError:
                        stream_ctx = await client.chat.completions.create(
                            model=resolved_model,
                            messages=messages,
                            stream=True,
                        )
                    async with stream_ctx as stream:
                        async for chunk in stream:
                            parsed = _extract_chunk_usage(chunk)
                            if parsed:
                                usage_holder.update(parsed)
                            text = _extract_delta_text(chunk)
                            if text:
                                redacted = redact_assistant_text(text)
                                output_chars += len(redacted)
                                output_parts.append(redacted)
                                yield redacted
                else:
                    async for token in _stream_via_thread(client, resolved_model, messages, usage_holder):
                        output_chars += len(token)
                        output_parts.append(token)
                        yield token
            except ImportError:
                async for token in _stream_via_thread(client, resolved_model, messages, usage_holder):
                    output_chars += len(token)
                    output_parts.append(token)
                    yield token
    finally:
        duration_ms = int((time.perf_counter() - started) * 1000)
        try:
            from keprix.quotas.runtime import get_fairness_scheduler, get_quota_enforcer

            if scheduler_token is not None:
                await get_fairness_scheduler().release_slot(scheduler_token)
            if quota_recordable:
                tokens_in = int(usage_holder.get("input_tokens") or estimated_input_tokens)
                tokens_out = int(usage_holder.get("output_tokens") or max(1, output_chars // 4))
                await get_quota_enforcer().record_llm_usage(
                    quota_product_id,
                    tokens_in=tokens_in,
                    tokens_out=tokens_out,
                    session_id=session_id,
                )
                try:
                    from keprix.quotas.actor_enforcer import record_scopes

                    record_scopes(
                        service="llm",
                        user_id=user_id,
                        product_id=quota_product_id,
                        tokens=tokens_in + tokens_out,
                        calls=1,
                    )
                except Exception:
                    pass
        except Exception:
            pass
        try:
            await _record_web_chat_usage(
                provider=provider,
                model=resolved_model or model or "",
                usage_counts=usage_holder or None,
                user_id=user_id,
                session_id=session_id,
                duration_ms=duration_ms,
                note="stream completed without usage chunk",
                channel=channel,
            )
        except Exception:
            pass
        try:
            from keprix.transparency.config import generation_log_enabled
            from keprix.transparency.generation_log import get_generation_log_store

            if generation_log_enabled() and output_parts:
                get_generation_log_store().log_generation(
                    input_payload=user_text,
                    output_payload="".join(output_parts),
                    model_name=str(resolved_model or model or provider or "unknown"),
                    user_id=user_id or "local",
                    content_type="text",
                    feature_endpoint="chat",
                    session_id=session_id,
                    metadata={"channel": channel, "provider": provider},
                )
        except Exception:
            pass
        try:
            from keprix.billing.wallet.enforcer import debit_managed_call

            tokens_in = int(usage_holder.get("input_tokens") or estimated_input_tokens)
            tokens_out = int(usage_holder.get("output_tokens") or max(1, output_chars // 4))
            await debit_managed_call(
                user_id=user_id,
                model=resolved_model or model or "",
                input_tokens=tokens_in,
                output_tokens=tokens_out,
                channel=channel,
                run_id=session_id,
                user_supplied_api_key=provider.startswith(CUSTOM_PREFIX),
            )
        except Exception:
            pass


@dataclass
class ChatCompletionResult:
    text: str
    provider: str
    model: str
    duration_ms: int


async def complete_chat_completion(
    *,
    user_text: str,
    model_id: str | None,
    history: list[dict[str, Any]] | None = None,
    user_id: str | None = None,
    session_id: str | None = None,
    channel: str = "web_ui",
    include_codebase_context: bool = True,
) -> ChatCompletionResult:
    started = time.perf_counter()
    provider, model = parse_model_id(model_id)
    parts: list[str] = []
    async for token in stream_chat_completion(
        user_text=user_text,
        model_id=model_id,
        history=history,
        user_id=user_id,
        session_id=session_id,
        channel=channel,
        include_codebase_context=include_codebase_context,
    ):
        parts.append(token)
    duration_ms = int((time.perf_counter() - started) * 1000)
    return ChatCompletionResult(
        text="".join(parts).strip(),
        provider=provider,
        model=model,
        duration_ms=duration_ms,
    )
