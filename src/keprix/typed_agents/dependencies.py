"""Dependency injection containers for typed agents."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, Field, PrivateAttr


class DatabaseHandle(Protocol):
    def execute(self, query: str, params: dict[str, Any] | None = None) -> Any: ...


class HttpClient(Protocol):
    async def get(self, url: str, **kwargs: Any) -> Any: ...


class SearchClient(Protocol):
    async def search(self, query: str, *, limit: int = 5) -> list[dict[str, Any]]: ...


class VaultAccess:
    """Vault wrapper that never exposes secret values to prompts."""

    def __init__(self, user_id: str, *, labels: dict[str, str] | None = None) -> None:
        self.user_id = user_id
        self._labels = dict(labels or {})

    def list_secret_labels(self) -> list[str]:
        return sorted(self._labels.values())

    def has_secret(self, label: str) -> bool:
        return label in self._labels.values()

    def prompt_safe_summary(self) -> dict[str, Any]:
        return {"user_id": self.user_id, "secret_labels": self.list_secret_labels()}


@dataclass
class InMemoryDatabase:
    def execute(self, query: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        return [{"query": query, "params": params or {}}]


class AgentDependencies(BaseModel):
    """Safe dependency bundle injected into typed agent runs."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    workspace_id: str = "default"
    tenant_id: str | None = None
    user_id: str = "default"
    feature_flags: dict[str, bool] = Field(default_factory=dict)
    permissions: list[str] = Field(default_factory=list)

    _database: Any = PrivateAttr(default=None)
    _http_client: Any = PrivateAttr(default=None)
    _search_client: Any = PrivateAttr(default=None)
    _vault: VaultAccess | None = PrivateAttr(default=None)

    def attach_runtime(
        self,
        *,
        database: DatabaseHandle | None = None,
        http_client: HttpClient | None = None,
        search_client: SearchClient | None = None,
        vault: VaultAccess | None = None,
    ) -> AgentDependencies:
        self._database = database
        self._http_client = http_client
        self._search_client = search_client
        self._vault = vault
        return self

    @property
    def database(self) -> DatabaseHandle | None:
        return self._database

    @property
    def http_client(self) -> HttpClient | None:
        return self._http_client

    @property
    def search_client(self) -> SearchClient | None:
        return self._search_client

    @property
    def vault(self) -> VaultAccess | None:
        return self._vault

    def prompt_safe_dict(self) -> dict[str, Any]:
        payload = {
            "workspace_id": self.workspace_id,
            "tenant_id": self.tenant_id,
            "user_id": self.user_id,
            "feature_flags": dict(self.feature_flags),
            "permissions": list(self.permissions),
            "vault": self._vault.prompt_safe_summary() if self._vault else None,
            "has_database": self._database is not None,
            "has_http_client": self._http_client is not None,
            "has_search_client": self._search_client is not None,
        }
        return payload


class SupportDependencies(AgentDependencies):
    support_tier: str = "standard"
    ticket_queue: str = "general"


def build_support_dependencies(
    *,
    workspace_id: str = "default",
    user_id: str = "default",
    permissions: list[str] | None = None,
    feature_flags: dict[str, bool] | None = None,
    vault_labels: dict[str, str] | None = None,
) -> SupportDependencies:
    vault = VaultAccess(user_id, labels=vault_labels or {"smtp": "SMTP credentials"})
    deps = SupportDependencies(
        workspace_id=workspace_id,
        user_id=user_id,
        permissions=permissions or ["support.read", "support.respond"],
        feature_flags=feature_flags or {"escalation_enabled": True},
        support_tier="standard",
        ticket_queue="general",
    )
    return deps.attach_runtime(database=InMemoryDatabase(), vault=vault)
