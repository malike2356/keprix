"""Credential rotation schedule metadata tests."""

from __future__ import annotations

from keprix.proxy.config import ProxyConfig, RouteConfig, dump_proxy_config, load_proxy_config


def test_route_config_roundtrips_cache_and_rotation(tmp_path) -> None:
    path = tmp_path / "proxy.toml"
    config = ProxyConfig(
        routes=[
            RouteConfig(
                host="api.stripe.com",
                header_name="Authorization",
                secret_ref="stripe-secret-key",
                cache={"ttl": "60s"},
                rotation={"schedule": "90d", "reminder": "7d"},
            )
        ]
    )

    dump_proxy_config(config, path)
    loaded = load_proxy_config(path)

    assert loaded.routes[0].cache["ttl"] == "60s"
    assert loaded.routes[0].rotation["schedule"] == "90d"
