"""Product hook registry and compatibility adapters.

Core modules call this file instead of importing product modules directly.
Product modules can later register concrete hooks here; the compatibility
helpers keep existing product behavior working during the boundary migration.
"""

from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module
from typing import Any, Callable


BeforeToolHook = Callable[..., object]
AfterToolHook = Callable[..., object]
AfterTurnHook = Callable[..., object]


@dataclass(frozen=True)
class RegisteredHook:
    name: str
    hook: Callable[..., object]
    product: str


class ManagedAiExhausted(RuntimeError):
    """Core-facing managed AI exhaustion error."""

    def __init__(self, message: str, *, payload: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.payload = payload or {}

# ── Product prompt layer registry ───────────────────────────────────────
# Product modules register additional prompt layers here.  Each layer is
# rendered after the core layers and before the persona layer.  Layers are
# rendered in registration order.  The operator can opt out of specific
# product layers via ``KEPRIX_DISABLED_PROMPT_LAYERS`` (comma-separated
# layer names).

_PRODUCT_PROMPT_LAYERS: dict[str, RegisteredPromptLayer] = {}
_DISABLED_PROMPT_LAYERS: set[str] = set()


@dataclass(frozen=True)
class RegisteredPromptLayer:
    name: str
    product: str
    render: Callable[[], str]  # Returns the layer content string


def register_product_prompt_layer(
    name: str,
    product: str,
    render: Callable[[], str],
) -> None:
    """Register a product prompt layer for inclusion in the agent prompt.

    Args:
        name: Unique layer name (e.g. ``scout_governance``).
        product: Product name for attribution (e.g. ``scout``).
        render: Zero-arg callable that returns the layer content.
    """
    _PRODUCT_PROMPT_LAYERS[name] = RegisteredPromptLayer(
        name=name, product=product, render=render,
    )


def iter_product_prompt_layers() -> list[RegisteredPromptLayer]:
    """Return registered product prompt layers in registration order."""
    return [l for l in _PRODUCT_PROMPT_LAYERS.values()
            if l.name not in _DISABLED_PROMPT_LAYERS]


def disable_prompt_layer(name: str) -> None:
    """Prevent a product prompt layer from being included."""
    _DISABLED_PROMPT_LAYERS.add(name)


def enable_prompt_layer(name: str) -> None:
    """Re-enable a previously disabled product prompt layer."""
    _DISABLED_PROMPT_LAYERS.discard(name)


def clear_prompt_layers_for_tests() -> None:
    _PRODUCT_PROMPT_LAYERS.clear()
    _DISABLED_PROMPT_LAYERS.clear()


_BEFORE_TOOL_HOOKS: dict[str, RegisteredHook] = {}
_AFTER_TOOL_HOOKS: dict[str, RegisteredHook] = {}
_AFTER_TURN_HOOKS: dict[str, RegisteredHook] = {}


def register_before_tool_hook(name: str, hook: BeforeToolHook, *, product: str) -> None:
    _BEFORE_TOOL_HOOKS[name] = RegisteredHook(name=name, hook=hook, product=product)


def register_after_tool_hook(name: str, hook: AfterToolHook, *, product: str) -> None:
    _AFTER_TOOL_HOOKS[name] = RegisteredHook(name=name, hook=hook, product=product)


def register_after_turn_hook(name: str, hook: AfterTurnHook, *, product: str) -> None:
    _AFTER_TURN_HOOKS[name] = RegisteredHook(name=name, hook=hook, product=product)


def iter_before_tool_hooks() -> list[RegisteredHook]:
    return list(_BEFORE_TOOL_HOOKS.values())


def iter_after_tool_hooks() -> list[RegisteredHook]:
    return list(_AFTER_TOOL_HOOKS.values())


def iter_after_turn_hooks() -> list[RegisteredHook]:
    return list(_AFTER_TURN_HOOKS.values())


def clear_hooks_for_tests() -> None:
    _BEFORE_TOOL_HOOKS.clear()
    _AFTER_TOOL_HOOKS.clear()
    _AFTER_TURN_HOOKS.clear()


def _optional_module(module_name: str) -> Any | None:
    try:
        return import_module(module_name)
    except Exception:
        return None


def _raise_core_managed_exhausted(err: BaseException) -> None:
    if err.__class__.__name__ != "ManagedAiExhausted":
        raise err
    payload = getattr(err, "payload", None)
    raise ManagedAiExhausted(str(err), payload=payload if isinstance(payload, dict) else None) from err


def check_memory_write(
    content: str,
    *,
    message_id: str | None = None,
    memory_kind: str | None = None,
) -> str | None:
    module = _optional_module("keprix.channel_shield.memory_guard_sync")
    if module is None:
        return None
    return module.check_memory_write(
        content,
        message_id=message_id,
        memory_kind=memory_kind,
    )


def estimate_managed_message_tokens(messages: list[dict[str, Any]]) -> int:
    module = _optional_module("keprix.billing.wallet.enforcer")
    if module is None:
        return 0
    return int(module.estimate_message_tokens(messages))


def managed_usage_tokens_from_response(response: Any) -> tuple[int, int]:
    module = _optional_module("keprix.billing.wallet.enforcer")
    if module is None:
        return (0, 0)
    return module.usage_tokens_from_response(response)


def sync_assert_managed_call_allowed(
    *,
    user_id: str | None,
    model: str | None,
    estimated_tokens: int,
    user_supplied_api_key: bool,
) -> None:
    module = _optional_module("keprix.billing.wallet.enforcer")
    if module is None:
        return
    try:
        module.sync_assert_managed_call_allowed(
            user_id=user_id,
            model=model,
            estimated_tokens=estimated_tokens,
            user_supplied_api_key=user_supplied_api_key,
        )
    except Exception as err:
        _raise_core_managed_exhausted(err)


async def assert_managed_call_allowed(
    *,
    user_id: str | None,
    model: str | None,
    estimated_tokens: int,
    user_supplied_api_key: bool,
) -> None:
    module = _optional_module("keprix.billing.wallet.enforcer")
    if module is None:
        return
    try:
        await module.assert_managed_call_allowed(
            user_id=user_id,
            model=model,
            estimated_tokens=estimated_tokens,
            user_supplied_api_key=user_supplied_api_key,
        )
    except Exception as err:
        _raise_core_managed_exhausted(err)


def sync_debit_managed_call(
    *,
    user_id: str | None,
    model: str | None,
    input_tokens: int,
    output_tokens: int,
    channel: str,
    user_supplied_api_key: bool,
) -> None:
    module = _optional_module("keprix.billing.wallet.enforcer")
    if module is None:
        return
    module.sync_debit_managed_call(
        user_id=user_id,
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        channel=channel,
        user_supplied_api_key=user_supplied_api_key,
    )


async def debit_managed_call(
    *,
    user_id: str | None,
    model: str | None,
    input_tokens: int,
    output_tokens: int,
    channel: str,
    user_supplied_api_key: bool,
) -> None:
    module = _optional_module("keprix.billing.wallet.enforcer")
    if module is None:
        return
    await module.debit_managed_call(
        user_id=user_id,
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        channel=channel,
        user_supplied_api_key=user_supplied_api_key,
    )
