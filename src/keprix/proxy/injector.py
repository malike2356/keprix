"""Route matching and header injection."""

from __future__ import annotations

from keprix.proxy.config import ProxyConfig, RouteConfig
from keprix.proxy.rotation import CredentialRotationManager
from keprix.proxy.secret import Secret
from keprix.proxy.vault import VaultProvider, get_vault_provider


class CredentialInjector:
    def __init__(self, config: ProxyConfig, vault: VaultProvider | None = None) -> None:
        self.config = config
        self.vault = vault or get_vault_provider(config.vault)
        self.rotation = CredentialRotationManager(config, vault=self.vault)

    def route_for_host(self, host: str) -> RouteConfig | None:
        return self.config.route_for_host(host)

    def inject_headers(self, host: str, headers: dict[str, str]) -> dict[str, str]:
        route = self.route_for_host(host)
        if route is None or route.type != "header":
            return headers
        secret = self.fetch_secret(route)
        try:
            value = secret.expose()
            if route.scheme:
                value = f"{route.scheme} {value}"
            updated = dict(headers)
            updated[route.header_name] = value
            return updated
        finally:
            secret.clear()

    def fetch_secret(self, route: RouteConfig | str) -> Secret:
        if isinstance(route, str):
            return self.vault.fetch(route)
        return self.rotation.fetch_for_route(route)
