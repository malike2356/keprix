"""Parse and write ~/.keprix/proxy.toml."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    import tomllib
except ImportError:  # pragma: no cover - py311 has tomllib
    import tomli as tomllib  # type: ignore[no-redef]

from keprix.proxy.paths import proxy_config_path


@dataclass
class RouteConfig:
    host: str
    header_name: str
    secret_ref: str
    type: str = "header"
    scheme: str | None = None
    cache: Any = "none"
    rotation: dict[str, Any] = field(default_factory=dict)


@dataclass
class ProxyConfig:
    listen: str = "127.0.0.1:6790"
    vault: str = "keychain"
    log_level: str = "warn"
    routes: list[RouteConfig] = field(default_factory=list)

    def route_for_host(self, host: str) -> RouteConfig | None:
        host = host.lower().split(":")[0]
        for route in self.routes:
            if route.host.lower() == host:
                return route
        return None


def _parse_route(raw: dict[str, Any]) -> RouteConfig:
    return RouteConfig(
        host=str(raw["host"]),
        header_name=str(raw["header_name"]),
        secret_ref=str(raw["secret_ref"]),
        type=str(raw.get("type", "header")),
        scheme=str(raw["scheme"]) if raw.get("scheme") else None,
        cache=raw.get("cache", "none"),
        rotation=raw.get("rotation", {}) if isinstance(raw.get("rotation", {}), dict) else {},
    )


def load_proxy_config(path: Path | None = None) -> ProxyConfig:
    cfg_path = path or proxy_config_path()
    if not cfg_path.is_file():
        return ProxyConfig()
    data = tomllib.loads(cfg_path.read_text(encoding="utf-8"))
    proxy = data.get("proxy", {})
    routes = [_parse_route(row) for row in data.get("routes", []) if isinstance(row, dict)]
    return ProxyConfig(
        listen=str(proxy.get("listen", "127.0.0.1:6790")),
        vault=str(proxy.get("vault", "keychain")),
        log_level=str(proxy.get("log_level", "warn")),
        routes=routes,
    )


def dump_proxy_config(config: ProxyConfig, path: Path | None = None) -> Path:
    cfg_path = path or proxy_config_path()
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "[proxy]",
        f'listen = "{config.listen}"',
        f'vault = "{config.vault}"',
        f'log_level = "{config.log_level}"',
        "",
    ]
    for route in config.routes:
        lines.append("[[routes]]")
        lines.append(f'host = "{route.host}"')
        lines.append(f'header_name = "{route.header_name}"')
        lines.append(f'type = "{route.type}"')
        lines.append(f'secret_ref = "{route.secret_ref}"')
        if route.scheme:
            lines.append(f'scheme = "{route.scheme}"')
        if route.cache and route.cache != "none":
            if isinstance(route.cache, dict):
                ttl = route.cache.get("ttl")
                if ttl:
                    lines.append(f'cache = {{ ttl = "{ttl}" }}')
            else:
                lines.append(f'cache = "{route.cache}"')
        if route.rotation:
            schedule = route.rotation.get("schedule")
            reminder = route.rotation.get("reminder")
            parts = []
            if schedule:
                parts.append(f'schedule = "{schedule}"')
            if reminder:
                parts.append(f'reminder = "{reminder}"')
            if parts:
                lines.append(f"rotation = {{ {', '.join(parts)} }}")
        lines.append("")
    cfg_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return cfg_path
