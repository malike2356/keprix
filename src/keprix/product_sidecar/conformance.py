"""Shared product-sidecar conformance runner (foundation release gate)."""

from __future__ import annotations

import hashlib
import json
import time
from typing import Any

from keprix.product_sidecar.auth import get_token_service, grants_for_product
from keprix.product_sidecar.connector import FakeProductConnector, run_connector_conformance
from keprix.product_sidecar.fixtures import FIXTURE_PRODUCT_KEYS, build_fixture_pack
from keprix.product_sidecar.openapi_contract import openapi_fragment, runtime_agrees_with_openapi
from keprix.product_sidecar.registry import PackValidationError, get_product_pack_registry
from keprix.product_sidecar.state import get_memory_store, reset_all_sidecar_state_for_tests


class ConformanceFailure(Exception):
    def __init__(self, must_failures: list[str]) -> None:
        super().__init__(", ".join(must_failures))
        self.must_failures = must_failures


def _sign_report(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


async def _invoke_fixture(product: str) -> dict[str, Any]:
    from keprix.product_sidecar.invoke import invoke_node
    from keprix.product_sidecar.types import RequestContext

    ctx = RequestContext(
        product=product,
        deployment="conformance",
        workspace_id="ws-conform",
        actor_id="conform",
        grants=grants_for_product(product),
        purpose="conformance",
        correlation_id=f"conform-{product}",
    )
    return await invoke_node(ctx, node_key="pack.ping", input_payload={"message": "conform"})


def run_foundation_conformance(*, include_fixtures: bool = True) -> dict[str, Any]:
    """Run Must checks. Any Must failure blocks READY."""
    must: list[dict[str, Any]] = []
    registry = get_product_pack_registry()

    # Registry coexistence
    keys = {p["product_key"] for p in registry.list_packs()}
    required = {"carina", "aiva"}
    if include_fixtures:
        required |= set(FIXTURE_PRODUCT_KEYS)
    missing = sorted(required - keys)
    must.append({"id": "packs_present", "ok": not missing, "detail": missing})

    namespaces = [p.get("memory_namespace") for p in registry.list_packs()]
    must.append(
        {
            "id": "namespace_unique",
            "ok": len(namespaces) == len(set(namespaces)),
            "detail": namespaces,
        }
    )

    # Malicious pack rejected
    try:
        registry.install(build_fixture_pack("abbis", corrupt=True))
        must.append({"id": "malicious_pack_rejected", "ok": False, "detail": "installed"})
    except PackValidationError:
        must.append({"id": "malicious_pack_rejected", "ok": True, "detail": "rejected"})

    # OpenAPI agreement
    agree = runtime_agrees_with_openapi("carina")
    must.append({"id": "openapi_runtime_agree", "ok": agree["ok"], "detail": agree.get("mismatches")})

    # Connector conformance
    fake = FakeProductConnector(product_key="abbis")
    conn = run_connector_conformance(fake)
    must.append({"id": "connector_default_deny", "ok": conn["ok"], "detail": conn["failures"]})

    # Token wrong audience / revoke
    tokens = get_token_service()
    token, claims = tokens.mint(
        product="carina",
        workspace_id="ws",
        actor_id="u",
        grants={"*"},
        purpose="t",
        audience="wrong-aud",
    )
    try:
        tokens.parse(token)
        must.append({"id": "wrong_audience", "ok": False})
    except ValueError as exc:
        must.append({"id": "wrong_audience", "ok": str(exc) == "wrong_audience"})

    good, good_claims = tokens.mint(
        product="carina",
        workspace_id="ws",
        actor_id="u",
        grants={"*"},
        purpose="t",
    )
    tokens.revoke(good_claims.jti)
    try:
        tokens.parse(good)
        must.append({"id": "revoked_token", "ok": False})
    except ValueError:
        must.append({"id": "revoked_token", "ok": True})

    # Cross-product composition
    try:
        registry.compose_nodes("carina", "clinicom")
        must.append({"id": "cross_product_compose", "ok": False})
    except PermissionError:
        must.append({"id": "cross_product_compose", "ok": True})

    # Memory isolation
    mem = get_memory_store()
    mem.put(product="abbis", workspace_id="ws1", key="k", value={"v": 1}, durable=True)
    leaked = mem.get(product="clinicom", workspace_id="ws1", key="k")
    must.append({"id": "cross_product_memory", "ok": leaked is None})

    # Kill switch
    registry.disable("petraclus")
    must.append({"id": "kill_switch", "ok": not registry.require("petraclus").enabled})
    registry.enable("petraclus")

    failures = [row["id"] for row in must if not row.get("ok")]
    report = {
        "suite": "keprix-sidecar-foundation",
        "contract_version": openapi_fragment()["x-keprix-contract-version"],
        "at": time.time(),
        "ready": not failures,
        "must": must,
        "must_failures": failures,
        "note": "Product packs still require their own owner pilot sign-off before production enablement.",
    }
    report["signature"] = _sign_report({k: v for k, v in report.items() if k != "signature"})
    # Ensure no secrets
    assert "secret" not in json.dumps(report).lower()
    if failures:
        raise ConformanceFailure(failures)
    return report


def run_foundation_conformance_safe() -> dict[str, Any]:
    try:
        return run_foundation_conformance()
    except ConformanceFailure as exc:
        return {
            "ready": False,
            "must_failures": exc.must_failures,
            "suite": "keprix-sidecar-foundation",
            "at": time.time(),
        }
