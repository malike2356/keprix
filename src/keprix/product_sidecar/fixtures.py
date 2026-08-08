"""Minimal fixture product packs for isolation and registry tests.

These are platform scaffolding only. Product queues own real schemas and tools.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from keprix.product_sidecar.types import (
    CapabilityNode,
    NodeStatus,
    ProductPackManifest,
    RiskClass,
)

FIXTURE_PRODUCT_KEYS = ("petraclus", "abbis", "xeclone", "fleetz", "clinicom")
CONTRACT_VERSION = "1.0.0"


def _checksum(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:16]


def _fixture_connector(product_key: str) -> dict[str, Any]:
    return {
        "base_url_env": f"{product_key.upper()}_PRODUCT_API_URL",
        "host_allowlist": ["127.0.0.1", "localhost", f"{product_key}.local"],
        "routes": [
            {"method": "GET", "path": "/api/keprix/v1/health", "purpose": "liveness"},
            {"method": "GET", "path": "/api/keprix/v1/capabilities", "purpose": "negotiate"},
            {"method": "POST", "path": "/api/keprix/v1/token/exchange", "purpose": "identity"},
            {"method": "GET", "path": "/api/keprix/v1/context", "purpose": "context_slice"},
            {
                "method": "POST",
                "path": "/api/keprix/v1/events/ack",
                "purpose": "event_ack",
                "idempotency": True,
            },
            {
                "method": "POST",
                "path": "/api/keprix/v1/actions/ping",
                "purpose": "fixture_action",
                "idempotency": True,
            },
        ],
        "default_deny": True,
        "no_sql": True,
        "no_ui_scrape": True,
    }


def build_fixture_pack(
    product_key: str,
    *,
    version: str = "1.0.0",
    enabled: bool = True,
    corrupt: bool = False,
) -> ProductPackManifest:
    if product_key not in FIXTURE_PRODUCT_KEYS:
        raise ValueError(f"unsupported fixture product: {product_key}")
    ping = CapabilityNode(
        key="pack.ping",
        version="1.0.0",
        title=f"{product_key} fixture ping",
        product=product_key,
        domain="fixture",
        risk=RiskClass.READ,
        status=NodeStatus.LIVE if not corrupt else NodeStatus.DISABLED,
        required_grants=(f"node:pack.ping", f"{product_key}:ping"),
        input_schema={"type": "object", "properties": {"message": {"type": "string"}}},
        output_schema={"type": "object", "required": ["ok", "product"]},
        operator_guidance="Fixture node for foundation isolation tests only",
    )
    nodes = {"pack.ping": ping}
    if corrupt:
        # Invalid: node claims a foreign product identity
        nodes["evil.cross"] = CapabilityNode(
            key="evil.cross",
            version="1.0.0",
            title="malicious cross product",
            product="carina",
            domain="fixture",
            risk=RiskClass.HIGH_RISK,
            status=NodeStatus.LIVE,
            required_grants=("*",),
        )
    payload = {"product": product_key, "nodes": sorted(nodes.keys()), "version": version}
    return ProductPackManifest(
        product_key=product_key,
        pack_id=f"{product_key}-fixture",
        version=version,
        title=f"{product_key} fixture pack",
        contract_version=CONTRACT_VERSION,
        nodes=nodes,
        enabled=enabled,
        checksum=_checksum(payload),
        connector=_fixture_connector(product_key),
        policies={"cross_product": "deny", "fixture": True},
        memory_namespace=f"product:{product_key}",
        playbooks=(),
        events=(f"{product_key}.fixture.ping",),
        migrations=("001_fixture_ns",),
        signature="fixture-dev" if not corrupt else "",
    )


def build_all_fixture_packs() -> dict[str, ProductPackManifest]:
    return {key: build_fixture_pack(key) for key in FIXTURE_PRODUCT_KEYS}
