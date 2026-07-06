"""Tool adapter base types (Prompt 56)."""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


WRITE_ACTIONS = frozenset({"write", "insert", "update", "delete", "execute", "invoke", "scrape"})


@dataclass
class AdapterCitation:
    title: str
    url: str
    snippet: str = ""
    source: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "url": self.url,
            "snippet": self.snippet,
            "source": self.source,
        }


@dataclass
class AdapterResult:
    ok: bool
    dry_run: bool = False
    data: dict[str, Any] = field(default_factory=dict)
    citations: list[AdapterCitation] = field(default_factory=list)
    setup_guidance: str | None = None
    error: str | None = None
    cost_estimate_usd: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "dry_run": self.dry_run,
            "data": self.data,
            "citations": [item.to_dict() for item in self.citations],
            "setup_guidance": self.setup_guidance,
            "error": self.error,
            "cost_estimate_usd": self.cost_estimate_usd,
        }


class ToolAdapter(ABC):
    name: str
    category: str
    required_env: tuple[str, ...] = ()
    risk_level: str = "low"
    supports_dry_run: bool = True
    requires_approval_for_write: bool = False
    supports_citations: bool = False
    setup_doc: str = ""
    optional_packages: tuple[str, ...] = ()

    def missing_env(self) -> list[str]:
        return [key for key in self.required_env if not os.environ.get(key, "").strip()]

    def setup_guidance(self) -> str:
        missing = self.missing_env()
        if not missing:
            return ""
        env_hint = ", ".join(missing)
        package_hint = ""
        if self.optional_packages:
            package_hint = f" Optional packages: pip install {' '.join(self.optional_packages)}."
        return (
            f"Configure {env_hint} to enable {self.name}.{package_hint} "
            f"{self.setup_doc}".strip()
        )

    def metadata(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "category": self.category,
            "required_env": list(self.required_env),
            "risk_level": self.risk_level,
            "supports_dry_run": self.supports_dry_run,
            "requires_approval_for_write": self.requires_approval_for_write,
            "supports_citations": self.supports_citations,
            "configured": not self.missing_env(),
            "setup_guidance": self.setup_guidance() or None,
        }

    async def run(
        self,
        action: str,
        params: dict[str, Any],
        *,
        dry_run: bool = True,
        approved: bool = False,
    ) -> AdapterResult:
        missing = self.missing_env()
        if missing:
            return AdapterResult(ok=False, setup_guidance=self.setup_guidance())

        if self.requires_approval_for_write and action in WRITE_ACTIONS and not approved:
            if dry_run and self.supports_dry_run:
                preview = await self.preview(action, params)
                preview.dry_run = True
                return preview
            return AdapterResult(
                ok=False,
                error=f"{self.name} write action '{action}' requires explicit approval",
            )

        if dry_run and self.supports_dry_run:
            preview = await self.preview(action, params)
            preview.dry_run = True
            return preview

        return await self.execute(action, params)

    async def preview(self, action: str, params: dict[str, Any]) -> AdapterResult:
        return AdapterResult(
            ok=True,
            data={"action": action, "params": params, "adapter": self.name, "preview": True},
        )

    @abstractmethod
    async def execute(self, action: str, params: dict[str, Any]) -> AdapterResult:
        raise NotImplementedError
