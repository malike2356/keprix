"""Credential requirements contract for external-call tools."""

from __future__ import annotations

from dataclasses import dataclass
from functools import wraps
from typing import Any, Callable, Iterable


@dataclass(frozen=True)
class CredentialRoute:
    host: str
    header: str
    secret_ref: str
    scheme: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "host": self.host,
            "header": self.header,
            "scheme": self.scheme,
            "secret_ref": self.secret_ref,
        }


@dataclass(frozen=True)
class RegisteredCredentialTool:
    tool_name: str
    routes: tuple[CredentialRoute, ...]

    def to_dict(self) -> dict[str, Any]:
        return {"tool_name": self.tool_name, "routes": [route.to_dict() for route in self.routes]}


class ToolCredentialRegistry:
    """Central registry of all tool credential requirements."""

    def __init__(self) -> None:
        self._tools: dict[str, RegisteredCredentialTool] = {}

    def register(self, tool_name: str, routes: Iterable[CredentialRoute]) -> RegisteredCredentialTool:
        normalized = tuple(routes)
        if not normalized:
            raise ValueError("credential route list cannot be empty")
        record = RegisteredCredentialTool(tool_name=tool_name, routes=normalized)
        self._tools[tool_name] = record
        return record

    def get(self, tool_name: str) -> RegisteredCredentialTool | None:
        return self._tools.get(tool_name)

    def all(self) -> list[RegisteredCredentialTool]:
        return sorted(self._tools.values(), key=lambda item: item.tool_name)

    def clear(self) -> None:
        self._tools.clear()

    def audit_log(self, tool_name: str, route: CredentialRoute, status: str, **detail: Any) -> dict[str, Any]:
        from keprix.tools.credential_audit import record_credential_audit

        return record_credential_audit(
            tool=tool_name,
            route={"host": route.host, "path": detail.get("path", ""), "method": detail.get("method", "")},
            credential_ref=route.secret_ref,
            status=status,
            duration_ms=detail.get("duration_ms"),
            response_status=detail.get("response_status"),
            session_id=detail.get("session_id"),
        )


credential_registry = ToolCredentialRegistry()


def _tool_name(target: Any, explicit: str | None) -> str:
    if explicit:
        return explicit
    module = getattr(target, "__module__", "")
    name = getattr(target, "__qualname__", None) or getattr(target, "__name__", target.__class__.__name__)
    return f"{module}.{name}" if module else str(name)


def _credential_doc(routes: Iterable[CredentialRoute]) -> str:
    lines = ["", "Credential requirements:"]
    for route in routes:
        scheme = f"{route.scheme} " if route.scheme else ""
        lines.append(f"  - {route.secret_ref}: injected by proxy for {route.host} via {route.header}: {scheme}<secret>")
    lines.append("")
    lines.append("The proxy injects credentials. This tool never holds real API keys.")
    return "\n".join(lines)


def credential(*, routes: list[CredentialRoute], tool_name: str | None = None) -> Callable[[Any], Any]:
    """Declare proxy-injected credential routes for a tool class or function.

    The decorator is intentionally pass-through for classes. For functions, it
    preserves the call path and only attaches metadata; audit entries should be
    written by the proxy-aware HTTP layer or explicit `audit_log` calls.
    """

    def _decorate(target: Any) -> Any:
        name = _tool_name(target, tool_name)
        credential_registry.register(name, routes)
        setattr(target, "__credential_routes__", tuple(routes))
        doc = getattr(target, "__doc__", "") or ""
        setattr(target, "__doc__", doc.rstrip() + _credential_doc(routes))
        if isinstance(target, type):
            return target

        @wraps(target)
        def _wrapped(*args: Any, **kwargs: Any) -> Any:
            return target(*args, **kwargs)

        setattr(_wrapped, "__credential_routes__", tuple(routes))
        return _wrapped

    return _decorate
