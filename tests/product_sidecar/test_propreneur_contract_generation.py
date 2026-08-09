"""Prompt 637: canonical contract drift gates and live-operation honesty."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from keprix.product_sidecar.handlers import HANDLERS
from keprix.product_sidecar.honesty import assert_live_nodes_honest
from keprix.product_sidecar.packs.propreneur import build_propreneur_nodes
from keprix.product_sidecar.registry import _propreneur_connector, build_propreneur_pack
from keprix.product_sidecar.types import NodeStatus

KEPRIX_ROOT = Path(__file__).resolve().parents[2]
WORKSPACE = KEPRIX_ROOT.parent
CANONICAL = (
    KEPRIX_ROOT
    / "domain-packs"
    / "propreneur"
    / "contracts"
    / "propreneur-agent-capabilities.v1.json"
)
FIXTURES = (
    KEPRIX_ROOT
    / "domain-packs"
    / "propreneur"
    / "contracts"
    / "generated"
    / "propreneur_conformance_fixtures.v1.json"
)
GENERATOR = KEPRIX_ROOT / "scripts" / "generate_propreneur_agent_contract.py"


def test_generator_check_is_clean() -> None:
    proc = subprocess.run(
        [sys.executable, str(GENERATOR), "--check"],
        cwd=str(WORKSPACE),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout


def test_canonical_contract_shape() -> None:
    raw = json.loads(CANONICAL.read_text(encoding="utf-8"))
    assert raw["contract"] == "propreneur-agent-capabilities"
    assert raw["version"] == "1.3.0"
    assert raw["canonical"] is True
    assert raw["operation_count"] == len(raw["operations"])
    assert raw["operation_count"] >= 50
    statuses = {o.get("status") for o in raw["operations"]}
    assert "live" in statuses
    assert "approval_required" in statuses
    assert "proposal_only" in statuses
    assert "intentionally_forbidden" in statuses
    for op in raw["operations"]:
        assert op["operation_id"]
        assert op["required_scope"]
        assert op["risk_class"]
        assert "path_parameters" in op
        assert op.get("request_body") is None or isinstance(op["request_body"], dict)
        # Path params are never smuggled into body
        if op.get("path_parameters") and op.get("request_body"):
            body_keys = set((op["request_body"] or {}).keys())
            assert not set(op["path_parameters"]) & body_keys


def test_pack_nodes_match_generated_catalog() -> None:
    fixtures = json.loads(FIXTURES.read_text(encoding="utf-8"))
    nodes = build_propreneur_nodes()
    assert set(nodes) == set(fixtures["pack_node_keys"])
    pack = build_propreneur_pack()
    assert set(pack.nodes) == set(fixtures["pack_node_keys"])
    # No handwritten live advertisement without honesty prerequisites
    assert assert_live_nodes_honest(pack.nodes.values(), connector=pack.connector) == []


def test_connector_routes_include_generated_aiva_methods() -> None:
    connector = _propreneur_connector()
    routes = {(r["method"], r["path"]) for r in connector["routes"]}
    assert ("GET", "/api/aiva/v1/properties/{propertyId}") in routes
    assert ("PATCH", "/api/aiva/v1/properties/{propertyId}") in routes
    assert ("DELETE", "/api/aiva/v1/properties/{propertyId}") in routes
    assert ("POST", "/api/aiva/v1/properties") in routes
    fixtures = json.loads(FIXTURES.read_text(encoding="utf-8"))
    assert {f"{m} {p}" for m, p in routes} == set(fixtures["connector_route_keys"])


def test_live_operations_have_full_bindings() -> None:
    raw = json.loads(CANONICAL.read_text(encoding="utf-8"))
    executable = [
        o
        for o in raw["operations"]
        if o.get("status") in {"live", "approval_required"} and o.get("pack_nodes")
    ]
    assert executable
    for op in executable:
        assert op.get("http_method"), f"{op['operation_id']} executable without method"
        assert op.get("http_path"), f"{op['operation_id']} executable without route"
        assert op.get("handler_binding"), f"{op['operation_id']} executable without handler_binding"
        assert op.get("required_scope"), f"{op['operation_id']} executable without scope"
        assert op.get("risk_class"), f"{op['operation_id']} executable without risk"
        for node in op.get("pack_nodes") or []:
            assert node in HANDLERS, f"live op {op['operation_id']} pack node {node} missing HANDLERS"


def test_no_pack_node_silently_missing_from_canonical() -> None:
    raw = json.loads(CANONICAL.read_text(encoding="utf-8"))
    covered = set()
    for op in raw["operations"]:
        covered.update(op.get("pack_nodes") or [])
    nodes = build_propreneur_nodes()
    missing = set(nodes) - covered
    assert missing == set(), f"pack nodes missing from canonical: {sorted(missing)}"


def test_property_get_live_after_handler_registration() -> None:
    pack = build_propreneur_pack()
    assert pack.nodes["property_get"].status == NodeStatus.LIVE
    assert pack.nodes["property_create"].status == NodeStatus.APPROVAL_REQUIRED
    assert "property_get" in HANDLERS
    assert "contact_get" in HANDLERS
    assert "tenancy_archive" in HANDLERS
    assert "project_create" in HANDLERS
    assert "sourcing_update" in HANDLERS
    assert "appointment_cancel" in HANDLERS
