"""Channel adapter registry for gateway health checks."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class ChannelAdapter(Protocol):
    name: str

    async def health_check(self) -> None: ...

    async def reconnect(self) -> None: ...


_REGISTRY: dict[str, ChannelAdapter] = {}


def register_adapter(adapter: ChannelAdapter) -> None:
    _REGISTRY[adapter.name] = adapter


def unregister_adapter(name: str) -> None:
    _REGISTRY.pop(name, None)


def get_adapter(name: str) -> ChannelAdapter | None:
    return _REGISTRY.get(name)


def get_active_adapters() -> list[ChannelAdapter]:
    if _REGISTRY:
        return list(_REGISTRY.values())

    adapters: list[ChannelAdapter] = []
    try:
        from keprix_cli.config import load_config

        cfg = load_config()
        gateway = cfg.get("gateway") or {}
        platforms = gateway.get("platforms") or {}
        for platform_name, platform_cfg in platforms.items():
            if not isinstance(platform_cfg, dict):
                continue
            if not platform_cfg.get("enabled", False):
                continue
            adapters.append(_ConfiguredChannelAdapter(str(platform_name)))
    except Exception:
        pass
    return adapters


def clear_registry() -> None:
    _REGISTRY.clear()


class _ConfiguredChannelAdapter:
    """Placeholder adapter for configured but not live-registered platforms."""

    def __init__(self, name: str) -> None:
        self.name = name

    async def health_check(self) -> None:
        try:
            from gateway.status import get_running_pid
            from keprix_cli.config import get_keprix_home

            pid_path = get_keprix_home() / "gateway.pid"
            if get_running_pid(pid_path, cleanup_stale=False) is None:
                raise RuntimeError("gateway is not running")
        except RuntimeError:
            raise
        except Exception as exc:
            raise RuntimeError(str(exc)) from exc

    async def reconnect(self) -> None:
        raise RuntimeError("manual gateway restart required")
