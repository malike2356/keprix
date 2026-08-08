"""Adapter registry with feature flags and health aggregation."""

from __future__ import annotations

import os
import threading
from typing import Any

from keprix.discovery.limits import CircuitBreaker, RateLimiter
from keprix.discovery.models import AdapterHealth, AdapterHealthStatus, AdapterManifest
from keprix.discovery.protocol import DiscoveryAdapter


class AdapterNotFoundError(LookupError):
    pass


class AdapterNotConfiguredError(RuntimeError):
    def __init__(self, name: str, message: str | None = None) -> None:
        self.name = name
        super().__init__(message or f"Discovery adapter {name!r} is not configured")


class AdapterDisabledError(RuntimeError):
    def __init__(self, name: str, message: str | None = None) -> None:
        self.name = name
        super().__init__(message or f"Discovery adapter {name!r} is disabled")


class DiscoveryRegistry:
    def __init__(self) -> None:
        self._adapters: dict[str, DiscoveryAdapter] = {}
        self._rate: dict[str, RateLimiter] = {}
        self._circuits: dict[str, CircuitBreaker] = {}
        self._lock = threading.RLock()
        self._bootstrapped = False

    def register(self, adapter: DiscoveryAdapter, *, replace: bool = False) -> None:
        name = adapter.name
        with self._lock:
            if name in self._adapters and not replace:
                raise ValueError(f"adapter already registered: {name}")
            self._adapters[name] = adapter
            rpm = int(adapter.manifest.rate_limit_per_minute or 30)
            self._rate[name] = RateLimiter(per_minute=rpm)
            self._circuits[name] = CircuitBreaker()

    def get(self, name: str) -> DiscoveryAdapter:
        self.ensure_builtin()
        with self._lock:
            adapter = self._adapters.get(name)
        if not adapter:
            raise AdapterNotFoundError(name)
        return adapter

    def list_names(self) -> list[str]:
        self.ensure_builtin()
        with self._lock:
            return sorted(self._adapters)

    def list_manifests(self) -> list[dict[str, Any]]:
        self.ensure_builtin()
        out: list[dict[str, Any]] = []
        for name in self.list_names():
            adapter = self.get(name)
            health = self.health(name)
            manifest = adapter.manifest.to_dict()
            manifest["health"] = health.to_dict()
            manifest["feature_enabled"] = self.is_feature_enabled(adapter.manifest)
            out.append(manifest)
        return out

    def rate_limiter(self, name: str) -> RateLimiter:
        self.ensure_builtin()
        with self._lock:
            if name not in self._rate:
                self._rate[name] = RateLimiter()
            return self._rate[name]

    def circuit(self, name: str) -> CircuitBreaker:
        self.ensure_builtin()
        with self._lock:
            if name not in self._circuits:
                self._circuits[name] = CircuitBreaker()
            return self._circuits[name]

    def is_feature_enabled(self, manifest: AdapterManifest) -> bool:
        flag = manifest.feature_flag
        if not flag:
            return True
        raw = os.environ.get(flag, "0" if manifest.experimental else "1").strip().lower()
        if manifest.experimental:
            return raw in {"1", "true", "yes", "on"}
        return raw not in {"0", "false", "no", "off"}

    def require_ready(self, name: str) -> DiscoveryAdapter:
        adapter = self.get(name)
        if not self.is_feature_enabled(adapter.manifest):
            raise AdapterDisabledError(
                name,
                f"Adapter {name!r} is disabled "
                f"(set {adapter.manifest.feature_flag}=1 to enable experimental adapters).",
            )
        health = adapter.health()
        if health.status == AdapterHealthStatus.NOT_CONFIGURED:
            raise AdapterNotConfiguredError(name, health.message or f"{name} not configured")
        if health.status == AdapterHealthStatus.DISABLED:
            raise AdapterDisabledError(name, health.message or f"{name} disabled")
        if not self.circuit(name).allow():
            raise AdapterDisabledError(name, f"Adapter {name!r} circuit breaker is open")
        return adapter

    def health(self, name: str) -> AdapterHealth:
        adapter = self.get(name)
        try:
            health = adapter.health()
        except Exception as exc:  # noqa: BLE001 - health must never raise to callers
            return AdapterHealth(
                name=name,
                status=AdapterHealthStatus.ERROR,
                message=str(exc),
                configured=False,
                enabled=False,
            )
        if not self.is_feature_enabled(adapter.manifest):
            return AdapterHealth(
                name=name,
                status=AdapterHealthStatus.DISABLED,
                message=f"Feature flag {adapter.manifest.feature_flag} is off",
                configured=health.configured,
                enabled=False,
                details=health.details,
            )
        if not self.circuit(name).allow():
            return AdapterHealth(
                name=name,
                status=AdapterHealthStatus.CIRCUIT_OPEN,
                message="Circuit breaker open after repeated failures",
                configured=health.configured,
                enabled=True,
                details=health.details,
            )
        return health

    def health_all(self) -> list[dict[str, Any]]:
        return [self.health(name).to_dict() for name in self.list_names()]

    def ensure_builtin(self) -> None:
        with self._lock:
            if self._bootstrapped:
                return
            self._bootstrapped = True
        # Import outside lock to avoid circular init deadlocks.
        from keprix.discovery.adapters import register_builtin_adapters

        register_builtin_adapters(self)

    def reset_for_tests(self) -> None:
        with self._lock:
            self._adapters.clear()
            self._rate.clear()
            self._circuits.clear()
            self._bootstrapped = False


_REGISTRY = DiscoveryRegistry()


def get_discovery_registry() -> DiscoveryRegistry:
    return _REGISTRY


def reset_discovery_registry_for_tests() -> DiscoveryRegistry:
    _REGISTRY.reset_for_tests()
    return _REGISTRY
