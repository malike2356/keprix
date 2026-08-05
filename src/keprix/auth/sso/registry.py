"""Register workspace SSO providers from environment configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass

from keprix.auth.sso.models import SsoProfile, SsoProviderError
from keprix.auth.sso.providers import github, google, oidc_generic


@dataclass(frozen=True)
class SsoProviderConfig:
    name: str
    display_name: str
    client_id: str
    client_secret: str
    issuer: str | None = None

    async def authorization_url(self, *, state: str, redirect_uri: str) -> str:
        if self.name == "google":
            return google.authorization_url(
                client_id=self.client_id,
                state=state,
                redirect_uri=redirect_uri,
            )
        if self.name == "github":
            return github.authorization_url(
                client_id=self.client_id,
                state=state,
                redirect_uri=redirect_uri,
            )
        if self.name == "oidc":
            if not self.issuer:
                raise SsoProviderError("OIDC issuer is not configured")
            discovery = await oidc_generic._discovery(self.issuer)
            return oidc_generic.authorization_url(
                client_id=self.client_id,
                state=state,
                redirect_uri=redirect_uri,
                issuer=self.issuer,
                discovery=discovery,
            )
        raise SsoProviderError(f"Unknown provider: {self.name}")

    async def exchange_code(self, *, code: str, redirect_uri: str) -> SsoProfile:
        if self.name == "google":
            return await google.exchange_code(
                client_id=self.client_id,
                client_secret=self.client_secret,
                code=code,
                redirect_uri=redirect_uri,
            )
        if self.name == "github":
            return await github.exchange_code(
                client_id=self.client_id,
                client_secret=self.client_secret,
                code=code,
                redirect_uri=redirect_uri,
            )
        if self.name == "oidc":
            if not self.issuer:
                raise SsoProviderError("OIDC issuer is not configured")
            return await oidc_generic.exchange_code(
                client_id=self.client_id,
                client_secret=self.client_secret,
                code=code,
                redirect_uri=redirect_uri,
                issuer=self.issuer,
            )
        raise SsoProviderError(f"Unknown provider: {self.name}")


def _env(name: str) -> str:
    return os.getenv(name, "").strip()


def _load_providers() -> dict[str, SsoProviderConfig]:
    providers: dict[str, SsoProviderConfig] = {}

    google_id = _env("KEPRIX_GOOGLE_CLIENT_ID")
    google_secret = _env("KEPRIX_GOOGLE_CLIENT_SECRET")
    if google_id and google_secret:
        providers["google"] = SsoProviderConfig(
            name="google",
            display_name="Google",
            client_id=google_id,
            client_secret=google_secret,
        )

    github_id = _env("KEPRIX_GITHUB_CLIENT_ID")
    github_secret = _env("KEPRIX_GITHUB_CLIENT_SECRET")
    if github_id and github_secret:
        providers["github"] = SsoProviderConfig(
            name="github",
            display_name="GitHub",
            client_id=github_id,
            client_secret=github_secret,
        )

    oidc_id = _env("KEPRIX_OIDC_CLIENT_ID")
    oidc_secret = _env("KEPRIX_OIDC_CLIENT_SECRET")
    oidc_issuer = _env("KEPRIX_OIDC_ISSUER")
    if oidc_id and oidc_secret and oidc_issuer:
        display = _env("KEPRIX_OIDC_NAME") or "OpenID Connect"
        providers["oidc"] = SsoProviderConfig(
            name="oidc",
            display_name=display,
            client_id=oidc_id,
            client_secret=oidc_secret,
            issuer=oidc_issuer,
        )

    return providers


_REGISTRY: dict[str, SsoProviderConfig] | None = None


def _registry() -> dict[str, SsoProviderConfig]:
    global _REGISTRY
    if _REGISTRY is None:
        _REGISTRY = _load_providers()
    return _REGISTRY


def reload_registry() -> None:
    global _REGISTRY
    _REGISTRY = _load_providers()


def list_providers() -> list[dict[str, str]]:
    return [
        {"name": provider.name, "display_name": provider.display_name}
        for provider in _registry().values()
    ]


def get_provider(name: str) -> SsoProviderConfig | None:
    return _registry().get(name.strip().lower())
