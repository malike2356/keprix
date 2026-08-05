"""provider_config agent tool: conversational BYOK / default model setup."""

from __future__ import annotations

import asyncio
import json
from typing import Any

from tools.registry import registry


def check_provider_config_requirements() -> bool:
    return True


def _run_async(coro):
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    if loop and loop.is_running():
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(asyncio.run, coro).result()
    return asyncio.run(coro)


def provider_config_tool(
    action: str,
    provider_id: str | None = None,
    credentials: dict[str, Any] | None = None,
    session_id: str | None = None,
) -> str:
    from keprix.configure import provider_config_service as svc

    act = (action or "").strip().lower()
    if act == "list":
        return json.dumps(svc.list_providers_payload(), ensure_ascii=False)

    if act == "requirements":
        if not provider_id:
            return json.dumps({"ok": False, "error": "provider_id is required"}, ensure_ascii=False)
        return json.dumps(svc.requirements_payload(provider_id), ensure_ascii=False)

    if act == "collect":
        if not provider_id:
            return json.dumps({"ok": False, "error": "provider_id is required"}, ensure_ascii=False)
        creds = {str(k): str(v) for k, v in (credentials or {}).items() if v is not None}
        result = _run_async(
            svc.collect_and_maybe_save(provider_id, creds or None, session_id=session_id)
        )
        result.pop("credentials", None)
        return json.dumps(result, ensure_ascii=False)

    if act == "configure":
        if not provider_id:
            return json.dumps({"ok": False, "error": "provider_id is required"}, ensure_ascii=False)
        creds = {str(k): str(v) for k, v in (credentials or {}).items() if v is not None}
        result = svc.configure_provider(provider_id, creds)
        result.pop("credentials", None)
        return json.dumps(result, ensure_ascii=False)

    if act == "test":
        if not provider_id:
            return json.dumps({"success": False, "message": "provider_id is required"}, ensure_ascii=False)
        return json.dumps(svc.test_provider_payload(provider_id), ensure_ascii=False)

    if act == "remove":
        if not provider_id:
            return json.dumps({"ok": False, "error": "provider_id is required"}, ensure_ascii=False)
        return json.dumps(svc.remove_provider_payload(provider_id), ensure_ascii=False)

    if act in {"set_default", "setdefault", "default"}:
        if not provider_id:
            return json.dumps({"ok": False, "error": "provider_id is required"}, ensure_ascii=False)
        return json.dumps(svc.set_default_payload(provider_id), ensure_ascii=False)

    return json.dumps(
        {
            "ok": False,
            "error": (
                f"Unknown action '{action}'. "
                "Use list | requirements | collect | configure | test | remove | set_default."
            ),
        },
        ensure_ascii=False,
    )


PROVIDER_CONFIG_SCHEMA = {
    "name": "provider_config",
    "description": (
        "Manage LLM provider API keys (BYOK) and default model selection. "
        "Actions: list | requirements | collect | configure | test | remove | set_default. "
        "Use collect for BotFather-style one-field-at-a-time setup "
        "(OpenAI, Anthropic, DeepSeek, Groq, OpenRouter, Ollama, ...). "
        "Never tell the user to dig through Settings pages. Never repeat API keys."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": [
                    "list",
                    "requirements",
                    "collect",
                    "configure",
                    "test",
                    "remove",
                    "set_default",
                ],
            },
            "provider_id": {
                "type": "string",
                "description": "Provider id or alias (openai, gpt, anthropic, claude, deepseek, groq, ...).",
            },
            "credentials": {
                "type": "object",
                "additionalProperties": {"type": "string"},
                "description": "Field keys such as api_key, default_model, host.",
            },
            "session_id": {"type": "string"},
        },
        "required": ["action"],
    },
}

registry.register(
    name="provider_config",
    toolset="providers",
    schema=PROVIDER_CONFIG_SCHEMA,
    handler=lambda args, **kw: provider_config_tool(
        action=str(args.get("action") or ""),
        provider_id=args.get("provider_id"),
        credentials=args.get("credentials") if isinstance(args.get("credentials"), dict) else None,
        session_id=args.get("session_id"),
    ),
    check_fn=check_provider_config_requirements,
    emoji="🔑",
    max_result_size_chars=50_000,
)
