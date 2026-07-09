"""Verify all configured proxy routes resolve secrets."""

from __future__ import annotations

from dataclasses import dataclass, field

from keprix.proxy.config import ProxyConfig, load_proxy_config
from keprix.proxy.vault import get_vault_provider


@dataclass
class VerifyReport:
    ok: bool = True
    lines: list[str] = field(default_factory=list)

    def add(self, message: str, *, ok: bool = True) -> None:
        prefix = "OK" if ok else "FAIL"
        self.lines.append(f"[{prefix}] {message}")
        if not ok:
            self.ok = False


def verify_routes(config: ProxyConfig | None = None) -> VerifyReport:
    cfg = config or load_proxy_config()
    report = VerifyReport()
    provider = get_vault_provider(cfg.vault)
    if not cfg.routes:
        report.add("No routes configured", ok=False)
        return report
    for route in cfg.routes:
        try:
            secret = provider.fetch(route.secret_ref)
            secret.clear()
            report.add(f"{route.host} -> {route.secret_ref}")
        except Exception as exc:
            report.add(f"{route.host} -> {route.secret_ref}: {exc}", ok=False)
    return report
