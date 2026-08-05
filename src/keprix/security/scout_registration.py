"""Scout product registration on Keprix startup."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

from keprix.config.constants import PRODUCT_VERSION
from keprix.security.scout_config import resolve_scout_config
from keprix.security.scout_integration import emit_scout_signal
from keprix.security.scout_types import SignalCategory, SignalSeverity

logger = logging.getLogger(__name__)


@dataclass
class ProductRegistration:
    product_id: str
    product_name: str
    product_version: str
    keprix_version: str
    instance_id: str
    features: dict[str, Any] = field(default_factory=dict)
    security_profile: str = "standard"
    registered_at: str = ""
    last_heartbeat: str = ""
    status: str = "online"
    agent_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ScoutRegistration:
    """Registers Keprix product instances with Scout."""

    def __init__(self) -> None:
        self._config = resolve_scout_config()
        self._local_path = Path.home() / ".keprix" / "scout" / "registrations.json"

    @property
    def register_url(self) -> str:
        base = self._config.endpoint.rstrip("/")
        if base.endswith("/api/v1/agents/register"):
            return base
        return f"{base}/api/v1/agents/register"

    def _determine_profile(self, features: dict[str, Any], override: str | None = None) -> str:
        if override:
            return override
        billing = features.get("billing") if isinstance(features.get("billing"), dict) else {}
        if billing and billing.get("enabled"):
            return "maximum"
        a2a = features.get("a2a") if isinstance(features.get("a2a"), dict) else {}
        if a2a and a2a.get("enabled"):
            return "high"
        return "standard"

    async def register_manifest(
        self,
        *,
        product_id: str,
        product_name: str,
        product_version: str,
        features: dict[str, Any] | None = None,
        security_profile: str | None = None,
        instance_id: str | None = None,
    ) -> ProductRegistration:
        features = features or {}
        instance = instance_id or self._config.agent_id or f"keprix:{product_id}:local"
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        registration = ProductRegistration(
            product_id=product_id,
            product_name=product_name,
            product_version=product_version,
            keprix_version=PRODUCT_VERSION,
            instance_id=instance,
            features=features,
            security_profile=self._determine_profile(features, security_profile),
            registered_at=now,
            last_heartbeat=now,
            agent_id=f"keprix:{product_id}:{instance}",
        )
        await self._post_registration(registration)
        self._save_local(registration)
        emit_scout_signal(
            SignalCategory.GOVERNANCE,
            SignalSeverity.INFO,
            "agent.registered",
            f"product:{product_id}",
            registration.to_dict(),
        )
        return registration

    async def deregister(self, product_id: str) -> None:
        local = self._load_local()
        agents = dict(local.get("agents") or {})
        agents.pop(product_id, None)
        local["agents"] = agents
        self._write_local(local)
        emit_scout_signal(
            SignalCategory.GOVERNANCE,
            SignalSeverity.INFO,
            "agent.deregistered",
            f"product:{product_id}",
            {"product_id": product_id},
        )

    async def heartbeat(self, product_id: str) -> None:
        local = self._load_local()
        agents = dict(local.get("agents") or {})
        row = dict(agents.get(product_id) or {})
        if not row:
            return
        row["last_heartbeat"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        row["status"] = "online"
        agents[product_id] = row
        local["agents"] = agents
        self._write_local(local)

    async def register_all_enabled_products(self) -> list[ProductRegistration]:
        registrations: list[ProductRegistration] = []
        try:
            from keprix.products.loader import get_enabled_products

            for product_id, product in get_enabled_products().items():
                registrations.append(
                    await self.register_manifest(
                        product_id=product_id,
                        product_name=product.display_name or product_id,
                        product_version="0.0.0",
                        features=dict(product.feature_flags or {}),
                    )
                )
        except Exception:
            logger.debug("enabled products registration skipped", exc_info=True)

        try:
            from keprix.integrations.product_registry import list_registered_products

            for row in list_registered_products():
                pid = str(row.get("product_id") or "")
                if any(item.product_id == pid for item in registrations):
                    continue
                registrations.append(
                    await self.register_manifest(
                        product_id=pid,
                        product_name=pid,
                        product_version="0.0.0",
                        features={"tools": row.get("tools") or []},
                        security_profile=str(row.get("security_policy") or "standard"),
                    )
                )
        except Exception:
            pass

        if not registrations:
            registrations.append(
                await self.register_manifest(
                    product_id=self._config.product,
                    product_name="Keprix",
                    product_version=PRODUCT_VERSION,
                    features={},
                )
            )
        return registrations

    def list_local_registrations(self) -> list[dict[str, Any]]:
        return list((self._load_local().get("agents") or {}).values())

    async def _post_registration(self, registration: ProductRegistration) -> None:
        if not self._config.enabled or not self._config.api_key:
            return
        body = json.dumps(registration.to_dict(), separators=(",", ":"), sort_keys=True).encode("utf-8")
        headers = {
            "Authorization": f"Bearer {self._config.api_key}",
            "Content-Type": "application/json",
        }
        try:
            from keprix.governance.signing import sign_payload

            headers["X-Governance-Signature"] = f"sha256={sign_payload(self._config.api_key, body)}"
        except Exception:
            pass
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(self.register_url, content=body, headers=headers)
            if response.status_code >= 400:
                logger.warning("Scout registration failed status=%s", response.status_code)
        except Exception:
            logger.debug("Scout registration unreachable", exc_info=True)

    def _load_local(self) -> dict[str, Any]:
        if not self._local_path.exists():
            return {"agents": {}}
        try:
            return json.loads(self._local_path.read_text(encoding="utf-8"))
        except Exception:
            return {"agents": {}}

    def _write_local(self, data: dict[str, Any]) -> None:
        self._local_path.parent.mkdir(parents=True, exist_ok=True)
        self._local_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def _save_local(self, registration: ProductRegistration) -> None:
        local = self._load_local()
        agents = dict(local.get("agents") or {})
        agents[registration.product_id] = registration.to_dict()
        local["agents"] = agents
        self._write_local(local)
