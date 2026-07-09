"""Route management helpers."""

from __future__ import annotations

from keprix.proxy.config import ProxyConfig, RouteConfig, dump_proxy_config, load_proxy_config


def add_route(
    *,
    host: str,
    header_name: str,
    secret_ref: str,
    scheme: str | None = None,
) -> ProxyConfig:
    config = load_proxy_config()
    config.routes = [route for route in config.routes if route.host != host]
    config.routes.append(
        RouteConfig(
            host=host,
            header_name=header_name,
            secret_ref=secret_ref,
            scheme=scheme,
        )
    )
    dump_proxy_config(config)
    return config


def remove_route(host: str) -> ProxyConfig:
    config = load_proxy_config()
    config.routes = [route for route in config.routes if route.host != host]
    dump_proxy_config(config)
    return config


def list_routes() -> list[RouteConfig]:
    return load_proxy_config().routes
