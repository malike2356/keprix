"""Product config registry."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


ConfigProvider = Callable[[], object]


@dataclass(frozen=True)
class RegisteredConfig:
    name: str
    provider: ConfigProvider
    product: str


_CONFIGS: dict[str, RegisteredConfig] = {}


def register_config(name: str, provider: ConfigProvider, *, product: str) -> None:
    _CONFIGS[name] = RegisteredConfig(name=name, provider=provider, product=product)


def iter_configs() -> list[RegisteredConfig]:
    return list(_CONFIGS.values())


def clear_configs_for_tests() -> None:
    _CONFIGS.clear()

