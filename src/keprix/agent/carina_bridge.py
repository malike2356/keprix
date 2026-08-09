"""Carina/Aiva agent bridge: adapt Carina contract turns to Keprix LLM + tools."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable

import httpx

logger = logging.getLogger(__name__)

DEFAULT_MAX_ITERATIONS = 10
DEFAULT_TIMEOUT_SECONDS = 30.0
DEFAULT_MODEL = "deepseek-v4-pro"


@dataclass
class HttpToolSpec:
    name: str
    endpoint: str
    auth_header: str = ""
    parameters: dict[str, Any] = field(default_factory=dict)


@dataclass
class LlmTurn:
    content: str | None
    tool_calls: list[dict[str, Any]]
    finish_reason: str
    usage: dict[str, int]
    provider: str = ""
    model: str = ""


class CarinaToolRegistry:
    """Per-request tool routing: Keprix native first, then Carina HTTP tools."""

    def __init__(
        self,
        *,
        native_dispatch: Callable[[str, dict[str, Any]], Any] | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._http_tools: dict[str, HttpToolSpec] = {}
        self._schemas: dict[str, dict[str, Any]] = {}
        self._native_dispatch = native_dispatch or _default_native_dispatch
        self._http_client = http_client

    def register_schema(self, name: str, description: str, parameters: dict[str, Any]) -> None:
        self._schemas[name] = {
            "type": "function",
            "function": {
                "name": name,
                "description": description or name,
                "parameters": parameters or {"type": "object", "properties": {}},
            },
        }

    def register_http_tool(
        self,
        *,
        name: str,
        endpoint: str,
        auth_header: str = "",
        schema: dict[str, Any] | None = None,
    ) -> None:
        self._http_tools[name] = HttpToolSpec(
            name=name,
            endpoint=endpoint,
            auth_header=auth_header or "",
            parameters=schema or {},
        )
        if name not in self._schemas:
            self.register_schema(name, name, schema or {"type": "object", "properties": {}})

    def openai_tools(self) -> list[dict[str, Any]]:
        return list(self._schemas.values())

    def has_route(self, name: str) -> bool:
        if name in self._http_tools:
            return True
        return self._native_exists(name)

    def _native_exists(self, name: str) -> bool:
        try:
            from tools.registry import registry as native

            return native.get_entry(name) is not None
        except Exception:
            return False

    async def execute(self, name: str, arguments: dict[str, Any]) -> str:
        if self._native_exists(name):
            result = self._native_dispatch(name, arguments)
            if asyncio.iscoroutine(result):
                result = await result
            return _stringify_tool_result(result)

        spec = self._http_tools.get(name)
        if spec is None:
            raise CarinaToolNotRegistered(name)

        headers: dict[str, str] = {"Content-Type": "application/json"}
        if spec.auth_header:
            headers["Authorization"] = spec.auth_header

        client = self._http_client
        owns_client = client is None
        if owns_client:
            client = httpx.AsyncClient(timeout=20.0)
        assert client is not None
        try:
            response = await client.post(spec.endpoint, json=arguments, headers=headers)
            text = response.text
            if response.status_code >= 400:
                return json.dumps(
                    {
                        "error": f"Carina tool HTTP {response.status_code}",
                        "tool": name,
                        "body": text[:4000],
                    }
                )
            return text
        finally:
            if owns_client:
                await client.aclose()


class CarinaToolNotRegistered(Exception):
    def __init__(self, tool_name: str) -> None:
        self.tool_name = tool_name
        super().__init__(f"Carina tool not registered: {tool_name}")


class SessionStore:
    """Workspace-isolated session message store."""

    def __init__(self) -> None:
        self._sessions: dict[str, list[dict[str, Any]]] = {}
        self._lock = asyncio.Lock()

    @staticmethod
    def _key(workspace_id: str, session_id: str) -> str:
        return f"{workspace_id}::{session_id}"

    async def get(self, workspace_id: str, session_id: str) -> list[dict[str, Any]]:
        async with self._lock:
            return list(self._sessions.get(self._key(workspace_id, session_id), []))

    async def save(self, workspace_id: str, session_id: str, messages: list[dict[str, Any]]) -> None:
        async with self._lock:
            self._sessions[self._key(workspace_id, session_id)] = list(messages)

    async def clear_workspace(self, workspace_id: str) -> None:
        prefix = f"{workspace_id}::"
        async with self._lock:
            for key in [k for k in self._sessions if k.startswith(prefix)]:
                del self._sessions[key]


class ProviderPool:
    """LLM completion with primary + failover providers."""

    def __init__(
        self,
        *,
        complete_fn: Callable[..., Awaitable[LlmTurn]] | None = None,
        fallbacks: list[tuple[str, str]] | None = None,
    ) -> None:
        self._complete_fn = complete_fn or _default_complete
        self._fallbacks = fallbacks

    async def complete(
        self,
        *,
        model: str,
        temperature: float,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> LlmTurn:
        chain = _provider_chain(model, self._fallbacks)
        errors: list[str] = []
        for provider, resolved_model in chain:
            try:
                return await self._complete_fn(
                    provider=provider,
                    model=resolved_model,
                    temperature=temperature,
                    messages=messages,
                    tools=tools,
                )
            except Exception as exc:
                errors.append(f"{provider}:{resolved_model}: {exc}")
                logger.warning("Carina bridge provider failed (%s/%s): %s", provider, resolved_model, exc)
        raise RuntimeError("All providers failed: " + " | ".join(errors))


class CarinaAgentBridge:
    """Execute one Carina/Aiva agent turn against Keprix providers and tools."""

    def __init__(
        self,
        *,
        tool_registry: CarinaToolRegistry | None = None,
        provider_pool: ProviderPool | None = None,
        session_store: SessionStore | None = None,
        max_iterations: int = DEFAULT_MAX_ITERATIONS,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        scout: Any | None = None,
    ) -> None:
        self.tool_registry = tool_registry or CarinaToolRegistry()
        self.provider_pool = provider_pool or ProviderPool()
        self.session_store = session_store or SessionStore()
        self.max_iterations = max_iterations
        self.timeout_seconds = timeout_seconds
        self.scout = scout

    async def run(
        self,
        *,
        workspace_id: str,
        session_id: str | None,
        model: str,
        temperature: float,
        system_prompt: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        carina_tools: list[dict[str, Any]],
        scout: Any | None = None,
        worker_id: str | None = None,
        inject_worker_kb: bool = True,
        confidence: float | None = None,
        force_escalate: bool = False,
        escalation_enabled: bool = True,
    ) -> dict[str, Any]:
        if not workspace_id:
            raise ValueError("workspace_id is required")

        resolved_session = session_id or f"sess_{uuid.uuid4().hex[:12]}"
        scout_guard = scout if scout is not None else self.scout
        registry = CarinaToolRegistry(
            native_dispatch=self.tool_registry._native_dispatch,
            http_client=self.tool_registry._http_client,
        )

        for tool_def in tools or []:
            name = str(tool_def.get("name") or "").strip()
            if not name:
                continue
            registry.register_schema(
                name,
                str(tool_def.get("description") or name),
                tool_def.get("parameters") or {"type": "object", "properties": {}},
            )

        for tool_def in carina_tools or []:
            name = str(tool_def.get("name") or "").strip()
            endpoint = str(tool_def.get("http_endpoint") or "").strip()
            if not name or not endpoint:
                continue
            schema = tool_def.get("parameters") or registry._schemas.get(name, {}).get("function", {}).get(
                "parameters", {}
            )
            registry.register_http_tool(
                name=name,
                endpoint=endpoint,
                auth_header=str(tool_def.get("auth_header") or ""),
                schema=schema if isinstance(schema, dict) else {},
            )

        effective_system = system_prompt or ""
        if inject_worker_kb and worker_id:
            try:
                from keprix.worker_kb.inject import inject_worker_kb_into_system_prompt

                effective_system = await inject_worker_kb_into_system_prompt(
                    system_prompt=effective_system,
                    workspace_id=workspace_id,
                    worker_id=worker_id,
                    messages=messages or [],
                )
            except Exception:
                pass

        run_started = time.perf_counter()
        try:
            result = await asyncio.wait_for(
                self._run_loop(
                    workspace_id=workspace_id,
                    session_id=resolved_session,
                    model=model or DEFAULT_MODEL,
                    temperature=float(temperature if temperature is not None else 0.7),
                    system_prompt=effective_system,
                    messages=messages or [],
                    registry=registry,
                    scout=scout_guard,
                    worker_id=worker_id,
                    confidence=confidence,
                    force_escalate=force_escalate,
                    escalation_enabled=escalation_enabled,
                ),
                timeout=self.timeout_seconds,
            )
            _record_run_analytics(
                workspace_id=workspace_id,
                worker_id=worker_id or "default",
                model=model or DEFAULT_MODEL,
                duration_seconds=time.perf_counter() - run_started,
                usage=result.get("usage") if isinstance(result, dict) else None,
                error_type=(result.get("error") if isinstance(result, dict) else None),
            )
            return result
        except asyncio.TimeoutError:
            usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
            _record_run_analytics(
                workspace_id=workspace_id,
                worker_id=worker_id or "default",
                model=model or DEFAULT_MODEL,
                duration_seconds=time.perf_counter() - run_started,
                usage=usage,
                error_type="timeout",
            )
            return {
                "message": {
                    "role": "assistant",
                    "content": "Agent turn timed out before completion.",
                },
                "tool_calls": [],
                "finish_reason": "error",
                "session_id": resolved_session,
                "usage": usage,
                "error": "timeout",
            }

    async def _run_loop(
        self,
        *,
        workspace_id: str,
        session_id: str,
        model: str,
        temperature: float,
        system_prompt: str,
        messages: list[dict[str, Any]],
        registry: CarinaToolRegistry,
        scout: Any | None = None,
        worker_id: str | None = None,
        confidence: float | None = None,
        force_escalate: bool = False,
        escalation_enabled: bool = True,
    ) -> dict[str, Any]:
        prior = await self.session_store.get(workspace_id, session_id)
        conversation = _build_conversation(system_prompt, prior, messages)
        openai_tools = registry.openai_tools()
        usage_total = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        last_turn: LlmTurn | None = None

        for _ in range(self.max_iterations):
            if scout is not None:
                kill = scout.check_kill(workspace_id)
                if kill.active:
                    return _scout_suspended_response(session_id, usage_total, kill.reason)

                prompt_text = _conversation_prompt_text(conversation)
                filtered = await scout.filter_prompt(
                    workspace_id=workspace_id,
                    prompt=prompt_text,
                    session_id=session_id,
                    model=model,
                )
                if filtered.blocked:
                    return {
                        "message": {
                            "role": "assistant",
                            "content": filtered.reason or "Prompt blocked by Scout security filter.",
                        },
                        "tool_calls": [],
                        "finish_reason": "error",
                        "session_id": session_id,
                        "usage": usage_total,
                        "error": "scout_prompt_blocked",
                        "scout": {
                            "verdict": filtered.verdict,
                            "risk_score": filtered.risk_score,
                        },
                    }

            turn = await self.provider_pool.complete(
                model=model,
                temperature=temperature,
                messages=conversation,
                tools=openai_tools,
            )
            last_turn = turn
            _accumulate_usage(usage_total, turn.usage)

            if turn.tool_calls:
                for call in turn.tool_calls:
                    name = _tool_call_name(call)
                    if name and not registry.has_route(name):
                        raise CarinaToolNotRegistered(name)

                assistant_msg = {
                    "role": "assistant",
                    "content": turn.content,
                    "tool_calls": turn.tool_calls,
                }
                conversation.append(assistant_msg)

                for call in turn.tool_calls:
                    if scout is not None and scout.check_kill(workspace_id).active:
                        return _scout_suspended_response(session_id, usage_total)

                    name = _tool_call_name(call)
                    call_id = str(call.get("id") or f"call_{uuid.uuid4().hex[:8]}")
                    args = _tool_call_args(call)
                    tool_started = time.perf_counter()
                    try:
                        result_text = await registry.execute(name, args)
                    except CarinaToolNotRegistered:
                        raise
                    except Exception as exc:
                        result_text = json.dumps({"error": str(exc), "tool": name})
                    try:
                        from keprix.aiva_analytics.metrics import record_tool_call

                        record_tool_call(
                            workspace_id=workspace_id,
                            tool_name=name or "unknown",
                            duration_seconds=time.perf_counter() - tool_started,
                        )
                    except Exception:
                        pass

                    if scout is not None:
                        await scout.log_event(
                            workspace_id=workspace_id,
                            event_type="tool_call",
                            session_id=session_id,
                            model=model,
                            tool_name=name,
                            tool_args=args,
                            tool_result=result_text,
                        )

                    conversation.append(
                        {
                            "role": "tool",
                            "tool_call_id": call_id,
                            "content": result_text,
                        }
                    )
                continue

            conversation.append({"role": "assistant", "content": turn.content or ""})
            await self.session_store.save(workspace_id, session_id, _persistable_messages(conversation))

            if scout is not None:
                await scout.log_event(
                    workspace_id=workspace_id,
                    event_type="agent_response",
                    session_id=session_id,
                    model=model,
                    response=turn.content or "",
                )

            final_content = turn.content or ""
            escalation_meta = None
            if escalation_enabled or force_escalate:
                try:
                    from keprix.aiva_escalation.service import get_escalation_service

                    escalation_meta = get_escalation_service().maybe_escalate_turn(
                        workspace_id=workspace_id,
                        worker_id=worker_id or "default",
                        session_id=session_id,
                        messages=messages,
                        assistant_text=final_content,
                        explicit_confidence=confidence,
                        force=force_escalate,
                    )
                except Exception:
                    escalation_meta = None

            if escalation_meta and escalation_meta.get("escalated"):
                holding = str(escalation_meta.get("holding_message") or final_content)
                conversation[-1] = {"role": "assistant", "content": holding}
                await self.session_store.save(workspace_id, session_id, _persistable_messages(conversation))
                return {
                    "message": {
                        "role": "assistant",
                        "content": holding,
                    },
                    "tool_calls": [],
                    "finish_reason": "escalated",
                    "session_id": session_id,
                    "usage": usage_total,
                    "escalation": {
                        "id": (escalation_meta.get("escalation") or {}).get("id"),
                        "confidence": escalation_meta.get("confidence"),
                        "threshold": escalation_meta.get("threshold"),
                        "status": "pending",
                        "notify": escalation_meta.get("notify"),
                    },
                }

            return {
                "message": {
                    "role": "assistant",
                    "content": final_content,
                },
                "tool_calls": [],
                "finish_reason": turn.finish_reason or "stop",
                "session_id": session_id,
                "usage": usage_total,
            }

        # Hit max iterations while still producing tool calls: surface them.
        tool_calls = list(last_turn.tool_calls) if last_turn else []
        await self.session_store.save(workspace_id, session_id, _persistable_messages(conversation))
        return {
            "message": {
                "role": "assistant",
                "content": last_turn.content if last_turn else None,
                "tool_calls": tool_calls,
            },
            "tool_calls": tool_calls,
            "finish_reason": "tool_calls" if tool_calls else "stop",
            "session_id": session_id,
            "usage": usage_total,
            "error": "max_iterations",
        }


def _default_native_dispatch(name: str, args: dict[str, Any]) -> Any:
    from tools.registry import registry as native

    return native.dispatch(name, args)


def _stringify_tool_result(result: Any) -> str:
    if result is None:
        return ""
    if isinstance(result, str):
        return result
    try:
        return json.dumps(result)
    except TypeError:
        return str(result)


def _provider_chain(model: str, overrides: list[tuple[str, str]] | None) -> list[tuple[str, str]]:
    primary = _parse_model(model)
    chain = [primary]
    if overrides:
        for item in overrides:
            if item not in chain:
                chain.append(item)
    else:
        for item in _env_fallbacks():
            if item not in chain:
                chain.append(item)
    return chain


def _parse_model(model: str) -> tuple[str, str]:
    raw = (model or DEFAULT_MODEL).strip()
    if ":" in raw:
        provider, name = raw.split(":", 1)
        provider = provider.strip().lower() or "deepseek"
        name = name.strip() or DEFAULT_MODEL
        return provider, name
    try:
        from keprix.api.chat_inference import resolve_default_provider_model

        provider, _ = resolve_default_provider_model()
        return provider, raw
    except Exception:
        return "deepseek", raw or DEFAULT_MODEL


def _env_fallbacks() -> list[tuple[str, str]]:
    raw = os.environ.get("CARINA_KEPRIX_FALLBACK_MODELS", "").strip()
    if not raw:
        # Sensible defaults when env unset; still only used after primary fails.
        return [
            ("openai", "gpt-4.1-mini"),
            ("openrouter", "openrouter/auto"),
        ]
    out: list[tuple[str, str]] = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        if ":" in part:
            provider, model = part.split(":", 1)
            out.append((provider.strip().lower(), model.strip()))
        else:
            out.append(("deepseek", part))
    return out


async def _default_complete(
    *,
    provider: str,
    model: str,
    temperature: float,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]],
) -> LlmTurn:
    from agent.auxiliary_client import resolve_provider_client

    registry_provider = provider
    if provider == "google":
        registry_provider = "gemini"
    elif provider == "openai":
        registry_provider = "openai-api"

    client, resolved_model = resolve_provider_client(registry_provider, model, async_mode=True)
    if client is None:
        raise RuntimeError(f"Provider '{provider}' is not configured")

    kwargs: dict[str, Any] = {
        "model": resolved_model or model,
        "messages": messages,
        "temperature": temperature,
    }
    if tools:
        kwargs["tools"] = tools
        kwargs["tool_choice"] = "auto"
    if provider == "deepseek" and model == "deepseek-v4-flash":
        fast_thinking = os.environ.get("AIVA_DEEPSEEK_THINKING", "false").strip().lower()
        if fast_thinking not in {"1", "true", "yes", "on"}:
            kwargs["extra_body"] = {"thinking": {"type": "disabled"}}

    response = await client.chat.completions.create(**kwargs)
    choice = response.choices[0]
    message = choice.message
    tool_calls = _normalize_tool_calls(getattr(message, "tool_calls", None))
    usage = _usage_from_response(response)
    finish = str(getattr(choice, "finish_reason", None) or ("tool_calls" if tool_calls else "stop"))
    content = getattr(message, "content", None)
    return LlmTurn(
        content=content,
        tool_calls=tool_calls,
        finish_reason=finish,
        usage=usage,
        provider=provider,
        model=str(resolved_model or model),
    )


def _normalize_tool_calls(raw: Any) -> list[dict[str, Any]]:
    if not raw:
        return []
    out: list[dict[str, Any]] = []
    for item in raw:
        if isinstance(item, dict):
            out.append(item)
            continue
        fn = getattr(item, "function", None)
        out.append(
            {
                "id": str(getattr(item, "id", None) or f"call_{uuid.uuid4().hex[:8]}"),
                "type": "function",
                "function": {
                    "name": str(getattr(fn, "name", "") if fn is not None else ""),
                    "arguments": str(getattr(fn, "arguments", "{}") if fn is not None else "{}"),
                },
            }
        )
    return out


def _usage_from_response(response: Any) -> dict[str, int]:
    usage = getattr(response, "usage", None)
    if usage is None:
        return {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    prompt = int(getattr(usage, "prompt_tokens", 0) or 0)
    completion = int(getattr(usage, "completion_tokens", 0) or 0)
    total = int(getattr(usage, "total_tokens", 0) or (prompt + completion))
    return {
        "prompt_tokens": prompt,
        "completion_tokens": completion,
        "total_tokens": total,
    }


def _accumulate_usage(total: dict[str, int], part: dict[str, int]) -> None:
    for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
        total[key] = int(total.get(key, 0)) + int(part.get(key, 0) or 0)


def _tool_call_name(call: dict[str, Any]) -> str:
    fn = call.get("function") if isinstance(call.get("function"), dict) else {}
    return str(fn.get("name") or call.get("name") or "").strip()


def _tool_call_args(call: dict[str, Any]) -> dict[str, Any]:
    fn = call.get("function") if isinstance(call.get("function"), dict) else {}
    raw = fn.get("arguments", call.get("arguments", "{}"))
    if isinstance(raw, dict):
        return raw
    try:
        parsed = json.loads(raw or "{}")
        return parsed if isinstance(parsed, dict) else {"value": parsed}
    except json.JSONDecodeError:
        return {"raw": str(raw)}


def _build_conversation(
    system_prompt: str,
    prior: list[dict[str, Any]],
    incoming: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    conversation: list[dict[str, Any]] = []
    if system_prompt:
        conversation.append({"role": "system", "content": system_prompt})

    # When the caller sends a full multi-turn history, trust it.
    # When the caller sends only a fresh user turn, prepend prior session state.
    incoming_norm = []
    for msg in incoming or []:
        role = str(msg.get("role") or "").strip().lower()
        if role == "system" and system_prompt:
            continue
        incoming_norm.append(_normalize_message(msg))

    if len(incoming_norm) <= 1 and prior:
        conversation.extend(prior)
        for msg in incoming_norm:
            conversation.append(msg)
    else:
        conversation.extend(incoming_norm)
    return conversation


def _normalize_message(msg: dict[str, Any]) -> dict[str, Any]:
    role = str(msg.get("role") or "user").strip().lower()
    out: dict[str, Any] = {"role": role, "content": msg.get("content")}
    if role == "assistant" and msg.get("tool_calls"):
        out["tool_calls"] = msg["tool_calls"]
    if role == "tool":
        out["tool_call_id"] = msg.get("tool_call_id") or msg.get("id") or ""
    return out


def _persistable_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Drop leading system prompt from persisted session history."""
    out: list[dict[str, Any]] = []
    for msg in messages:
        if msg.get("role") == "system" and not out:
            continue
        out.append(msg)
    return out


def _conversation_prompt_text(messages: list[dict[str, Any]]) -> str:
    parts: list[str] = []
    for msg in messages:
        role = str(msg.get("role") or "")
        content = msg.get("content")
        if isinstance(content, str) and content.strip():
            parts.append(f"{role}: {content}")
        elif msg.get("tool_calls"):
            parts.append(f"{role}: [tool_calls]")
    return "\n".join(parts)[-12000:]


def _scout_suspended_response(
    session_id: str,
    usage: dict[str, int],
    reason: str = "",
) -> dict[str, Any]:
    return {
        "message": {
            "role": "assistant",
            "content": reason
            or "Agent execution suspended by Scout. Contact your administrator.",
        },
        "tool_calls": [],
        "finish_reason": "error",
        "session_id": session_id,
        "usage": usage,
        "error": "scout_kill_switch",
    }


def _record_run_analytics(
    *,
    workspace_id: str,
    worker_id: str,
    model: str,
    duration_seconds: float,
    usage: dict[str, Any] | None,
    error_type: str | None = None,
) -> None:
    try:
        from agent.usage_pricing import CanonicalUsage
        from keprix.aiva_analytics.metrics import record_agent_call, record_worker_message
        from keprix.usage.pricing_bridge import estimate_llm_cost
        from keprix.usage.recorder import get_llm_usage_recorder
    except Exception:
        return

    usage = usage or {}
    prompt_tokens = int(usage.get("prompt_tokens") or 0)
    completion_tokens = int(usage.get("completion_tokens") or 0)
    cost_usd = None
    try:
        canonical = CanonicalUsage(input_tokens=prompt_tokens, output_tokens=completion_tokens)
        cost = estimate_llm_cost(usage=canonical, model=model, provider="")
        if cost.amount_usd is not None:
            cost_usd = float(cost.amount_usd)
        recorder_kwargs = {
            "usage": canonical,
            "provider": "",
            "model": model,
            "channel": "aiva",
            "workspace_id": workspace_id,
            "duration_ms": int(max(0.0, duration_seconds) * 1000),
            "metadata": {"worker_id": worker_id, "source": "carina_bridge"},
            "cost_result": cost,
        }
        recorder = get_llm_usage_recorder()
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            recorder.record_sync(**recorder_kwargs)
        else:
            task = loop.create_task(recorder.record(**recorder_kwargs))
            task.add_done_callback(_consume_background_exception)
    except Exception:
        logger.debug("llm usage recorder skipped", exc_info=True)

    try:
        record_agent_call(
            workspace_id=workspace_id,
            worker_id=worker_id,
            model=model,
            duration_seconds=duration_seconds,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost_usd=cost_usd,
            error_type=str(error_type) if error_type else None,
        )
        record_worker_message(workspace_id, worker_id, channel="carina")
    except Exception:
        logger.debug("aiva analytics record skipped", exc_info=True)


def _consume_background_exception(task: asyncio.Task[Any]) -> None:
    """Retrieve background recorder exceptions without delaying the agent reply."""
    try:
        task.exception()
    except (asyncio.CancelledError, Exception):
        return
