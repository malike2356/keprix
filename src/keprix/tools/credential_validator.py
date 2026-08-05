"""Startup validation for tool credential contracts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from keprix.proxy.config import ProxyConfig, load_proxy_config
from keprix.proxy.pidfile import is_running
from keprix.proxy.vault import get_vault_provider
from keprix.tools.credential_contract import ToolCredentialRegistry, credential_registry


@dataclass(frozen=True)
class CredentialValidationResult:
    tool_name: str
    host: str
    secret_ref: str
    status: str
    message: str

    @property
    def ok(self) -> bool:
        return self.status == "ok"

    @property
    def fail(self) -> bool:
        return self.status == "fail"

    def to_dict(self) -> dict[str, Any]:
        return {
            "tool_name": self.tool_name,
            "host": self.host,
            "secret_ref": self.secret_ref,
            "status": self.status,
            "message": self.message,
        }


def validate_all(
    registry: ToolCredentialRegistry | None = None,
    *,
    config: ProxyConfig | None = None,
    proxy_running: bool | None = None,
) -> list[CredentialValidationResult]:
    registry = registry or credential_registry
    cfg = config or load_proxy_config()
    running = is_running() if proxy_running is None else proxy_running
    provider = get_vault_provider(cfg.vault)
    results: list[CredentialValidationResult] = []
    for tool in registry.all():
        for route in tool.routes:
            configured = cfg.route_for_host(route.host)
            if configured is None:
                results.append(
                    CredentialValidationResult(
                        tool_name=tool.tool_name,
                        host=route.host,
                        secret_ref=route.secret_ref,
                        status="fail",
                        message="route not configured in proxy.toml",
                    )
                )
                continue
            if configured.secret_ref != route.secret_ref or configured.header_name.lower() != route.header.lower():
                results.append(
                    CredentialValidationResult(
                        tool_name=tool.tool_name,
                        host=route.host,
                        secret_ref=route.secret_ref,
                        status="fail",
                        message="proxy route does not match declared credential contract",
                    )
                )
                continue
            if not running:
                results.append(
                    CredentialValidationResult(
                        tool_name=tool.tool_name,
                        host=route.host,
                        secret_ref=route.secret_ref,
                        status="fail",
                        message="credential proxy is not running",
                    )
                )
                continue
            try:
                secret = provider.fetch(route.secret_ref)
                secret.clear()
            except Exception as exc:
                results.append(
                    CredentialValidationResult(
                        tool_name=tool.tool_name,
                        host=route.host,
                        secret_ref=route.secret_ref,
                        status="warn",
                        message=f"secret not found in vault: {exc}",
                    )
                )
                continue
            results.append(
                CredentialValidationResult(
                    tool_name=tool.tool_name,
                    host=route.host,
                    secret_ref=route.secret_ref,
                    status="ok",
                    message="proxy running, route configured, secret found",
                )
            )
    return results


def validation_summary(results: list[CredentialValidationResult]) -> dict[str, Any]:
    return {
        "ok": not any(result.fail for result in results),
        "total": len(results),
        "ok_count": sum(1 for result in results if result.status == "ok"),
        "warn_count": sum(1 for result in results if result.status == "warn"),
        "fail_count": sum(1 for result in results if result.status == "fail"),
        "results": [result.to_dict() for result in results],
    }


def validate_or_raise() -> None:
    summary = validation_summary(validate_all())
    if summary["fail_count"]:
        rows = "\n".join(f"{row['tool_name']} -> {row['host']}: {row['message']}" for row in summary["results"] if row["status"] == "fail")
        raise RuntimeError(f"Tool credential isolation validation failed:\n{rows}\nRun: keprix proxy doctor --fix")
