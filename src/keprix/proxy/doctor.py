"""Diagnostic checks for credential proxy."""

from __future__ import annotations

from dataclasses import dataclass, field

from keprix.proxy.certs import ensure_ca_material
from keprix.proxy.config import ProxyConfig, load_proxy_config
from keprix.proxy.paths import proxy_config_path
from keprix.proxy.pidfile import is_running, read_pid
from keprix.proxy.vault import get_vault_provider


@dataclass
class DoctorReport:
    ok: bool = True
    lines: list[str] = field(default_factory=list)

    def add(self, message: str, *, ok: bool = True) -> None:
        prefix = "OK" if ok else "FAIL"
        self.lines.append(f"[{prefix}] {message}")
        if not ok:
            self.ok = False


def run_doctor(config: ProxyConfig | None = None) -> DoctorReport:
    report = DoctorReport()
    cfg = config or load_proxy_config()
    cfg_path = proxy_config_path()
    if cfg_path.is_file():
        report.add(f"Config found at {cfg_path}")
    else:
        report.add(f"Config missing at {cfg_path}", ok=False)

    host, _, port_text = cfg.listen.partition(":")
    if host in {"127.0.0.1", "::1", "localhost"}:
        report.add(f"Listen address is localhost-only ({cfg.listen})")
    else:
        report.add(f"Listen address must be localhost-only, got {cfg.listen}", ok=False)

    try:
        ca_cert, ca_key = ensure_ca_material()
        report.add(f"CA certificate ready at {ca_cert}")
        report.add(f"CA private key ready at {ca_key}")
    except Exception as exc:
        report.add(f"CA material error: {exc}", ok=False)

    provider = get_vault_provider(cfg.vault)
    if provider.is_available():
        report.add(f"Vault provider {cfg.vault!r} is available")
    else:
        report.add(f"Vault provider {cfg.vault!r} is not available", ok=False)

    for route in cfg.routes:
        try:
            secret = provider.fetch(route.secret_ref)
            secret.clear()
            report.add(f"Route {route.host} resolves secret {route.secret_ref!r}")
        except Exception as exc:
            report.add(f"Route {route.host} secret {route.secret_ref!r}: {exc}", ok=False)

    if is_running():
        report.add(f"Proxy process running (pid {read_pid()})")
    else:
        report.add("Proxy process is not running")

    return report
