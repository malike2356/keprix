#!/usr/bin/env python3
"""Generate the Propreneur/Keprix CRUD remediation gap report (prompt 636).

Inventories operations from every known source and writes a machine-readable
JSON report. Does not widen mutation behavior.
"""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

KEPRIX_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = KEPRIX_ROOT.parent
PROPRENEUR_ROOT = WORKSPACE / "propreneur"
OUT_PATH = KEPRIX_ROOT / "docs" / "architecture" / "propreneur-crud-remediation-gap-report.json"

sys.path.insert(0, str(KEPRIX_ROOT / "src"))

from keprix.product_sidecar.handlers import HANDLERS  # noqa: E402
from keprix.product_sidecar.honesty import (  # noqa: E402
    BEHAVIORAL_TEST_NODES,
    NODE_CONNECTOR_ROUTES,
    connector_route_ok,
    has_behavioral_test,
    has_executable_handler,
)
from keprix.product_sidecar.registry import (  # noqa: E402
    _propreneur_connector,
    build_propreneur_pack,
)


def _blank_row(**overrides: Any) -> dict[str, Any]:
    row = {
        "operation_id": "",
        "domain": "",
        "action": "",
        "http_method": "",
        "http_path": "",
        "agent_schema": "",
        "runtime_handler": "",
        "actor_source": "",
        "required_scope": "",
        "risk": "",
        "approval": "",
        "idempotency": "",
        "concurrency": "",
        "audit_event": "",
        "tests": "",
        "ui_equivalent": "",
        "rag_claim": "",
        "current_status": "",
        "sources": [],
        "notes": "",
    }
    row.update(overrides)
    return row


def _parse_openapi_operations(yaml_text: str) -> list[dict[str, Any]]:
    """Minimal OpenAPI path/method/operationId extractor (no full YAML dep)."""
    ops: list[dict[str, Any]] = []
    path = None
    method = None
    for line in yaml_text.splitlines():
        m_path = re.match(r"^  (/api/aiva/v1/\S+):\s*$", line)
        if m_path:
            path = m_path.group(1)
            method = None
            continue
        m_method = re.match(r"^    (get|post|put|patch|delete):\s*$", line, re.I)
        if m_method and path:
            method = m_method.group(1).upper()
            continue
        if method and path:
            m_op = re.match(r"^      operationId:\s*(\S+)\s*$", line)
            if m_op:
                ops.append(
                    {
                        "operation_id": m_op.group(1),
                        "http_method": method,
                        "http_path": path,
                    }
                )
                method = None
                continue
            m_tag = re.match(r"^      tags:\s*$", line)
            if m_tag:
                # operationId may appear after tags; keep waiting
                continue
            m_sum = re.match(r"^      summary:\s*(.+)\s*$", line)
            if m_sum and not any(
                o["http_method"] == method and o["http_path"] == path for o in ops
            ):
                # fallback id from method+path if operationId missing later
                pass
    return ops


def _php_tool_names(tools_dir: Path) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    if not tools_dir.is_dir():
        return out
    for path in sorted(tools_dir.glob("*Tool.php")):
        if path.name in {"CarinaTool.php", "DefinedCarinaTool.php", "PlatformCarinaTool.php"}:
            continue
        text = path.read_text(encoding="utf-8")
        m = re.search(
            r"public function name\(\)\s*:\s*string\s*\{\s*return\s*'([^']+)'",
            text,
            re.S,
        )
        if not m:
            m = re.search(r"public function name\(\)[^{]*\{\s*return\s*'([^']+)'", text, re.S)
        if m:
            out.append((m.group(1), path.name))
    return out


def _config_tool_names(php_path: Path) -> list[str]:
    if not php_path.is_file():
        return []
    return re.findall(r"'name'\s*=>\s*'([^']+)'", php_path.read_text(encoding="utf-8"))


def _infer_action(name: str) -> str:
    for token in (
        "search",
        "list",
        "get",
        "create",
        "update",
        "archive",
        "delete",
        "propose",
        "cancel",
        "invite",
        "sync",
        "ask",
    ):
        if token in name.replace("-", "_").lower():
            return token
    return "unknown"


def _infer_domain(name: str) -> str:
    n = name.replace("-", "_").lower()
    for domain in (
        "property",
        "contact",
        "tenancy",
        "deal",
        "compliance",
        "maintenance",
        "expense",
        "appointment",
        "document",
        "project",
        "owner",
        "sourcing",
        "portfolio",
        "task",
        "note",
        "finance",
        "team",
        "platform",
        "sync",
    ):
        if domain in n:
            return domain
    return "general"


def build_report() -> dict[str, Any]:
    pack = build_propreneur_pack()
    connector = _propreneur_connector()
    rows: dict[str, dict[str, Any]] = {}

    def upsert(op_id: str, **fields: Any) -> None:
        if op_id not in rows:
            rows[op_id] = _blank_row(operation_id=op_id)
        row = rows[op_id]
        for key, value in fields.items():
            if key == "sources":
                srcs = list(row.get("sources") or [])
                for item in value if isinstance(value, list) else [value]:
                    if item and item not in srcs:
                        srcs.append(item)
                row["sources"] = srcs
                continue
            if value in (None, ""):
                continue
            if not row.get(key):
                row[key] = value

    # Pack nodes
    for key, node in pack.nodes.items():
        handler = "HANDLERS[" + key + "]" if has_executable_handler(key) else ""
        route = NODE_CONNECTOR_ROUTES.get(key)
        upsert(
            key,
            domain=node.domain,
            action=_infer_action(key),
            http_method=route[0] if route else "",
            http_path=route[1] if route else "",
            agent_schema="product_sidecar.CapabilityNode",
            runtime_handler=handler or "missing",
            actor_source="RequestContext.actor_id (sidecar invoke)",
            required_scope=",".join(node.required_grants),
            risk=node.risk.value,
            approval="soft_wall" if node.soft_wall else "none",
            idempotency="yes" if node.idempotent else "mutation_key_required",
            concurrency="tenant_scoped",
            audit_event=f"product_sidecar.invoke:{key}",
            tests="registered" if has_behavioral_test(key) else "none_behavioral",
            ui_equivalent="",
            rag_claim="under_remediation",
            current_status=node.status.value,
            sources=["pack_nodes"],
            notes=(
                "Fail-closed: pack node advertised status after honesty resolve. "
                f"handler={has_executable_handler(key)} "
                f"route_ok={connector_route_ok(key, connector)} "
                f"test={has_behavioral_test(key)}"
            ),
        )

    # Contract tools
    contract_path = KEPRIX_ROOT / "domain-packs" / "propreneur" / "contracts" / "propreneur-aiva-tools.v1.json"
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    for tool in contract.get("tools") or []:
        name = str(tool.get("name") or "")
        upsert(
            name,
            domain=_infer_domain(name),
            action=_infer_action(name),
            agent_schema="propreneur-aiva-tools.v1",
            runtime_handler="contract_catalog_only",
            actor_source="Aiva linked actor / Propreneur session",
            required_scope=str(tool.get("scope") or ""),
            risk=str(tool.get("risk_class") or ""),
            approval=str(tool.get("approval") or ""),
            rag_claim="contract_listed",
            current_status="catalog",
            sources=["propreneur-aiva-tools.v1.json"],
            notes=str(tool.get("purpose") or "")[:240],
        )

    # Generated Aiva v1 tools
    gen_path = PROPRENEUR_ROOT / "docs" / "aiva" / "generated" / "aiva-v1-tools.json"
    if gen_path.is_file():
        gen = json.loads(gen_path.read_text(encoding="utf-8"))
        for tool in gen.get("tools") or []:
            name = str(tool.get("name") or "")
            upsert(
                name,
                domain=_infer_domain(name),
                action=_infer_action(name),
                http_method=str(tool.get("http_method") or ""),
                http_path=str(tool.get("path") or ""),
                agent_schema="aiva_v1_tools generated",
                runtime_handler="laravel_aiva_v1",
                actor_source="aiva.v1 middleware + delegated grant",
                required_scope=str(tool.get("scope_domain") or ""),
                risk=str(tool.get("risk_class") or ""),
                approval="",
                idempotency=str(tool.get("idempotency") or ""),
                concurrency=str(tool.get("etag") or ""),
                tests="AivaV1ApiTest (feature)",
                ui_equivalent="",
                rag_claim="openapi_generated",
                current_status="product_api_ready_pack_not_wired",
                sources=["aiva-v1-tools.json", "config/aiva_v1_tools.php"],
            )

    # OpenAPI operations
    oa_path = PROPRENEUR_ROOT / "docs" / "aiva" / "openapi-aiva-v1.yaml"
    if oa_path.is_file():
        for op in _parse_openapi_operations(oa_path.read_text(encoding="utf-8")):
            upsert(
                op["operation_id"],
                domain=_infer_domain(op["operation_id"]),
                action=_infer_action(op["operation_id"]),
                http_method=op["http_method"],
                http_path=op["http_path"],
                agent_schema="openapi-aiva-v1",
                runtime_handler="laravel_aiva_v1_controller",
                actor_source="aiva.v1",
                current_status="product_api",
                sources=["openapi-aiva-v1.yaml", "routes/tenant.php"],
            )

    # Native Carina tools
    for name, cls in _php_tool_names(PROPRENEUR_ROOT / "app" / "Services" / "Carina" / "Tools"):
        upsert(
            name,
            domain=_infer_domain(name),
            action=_infer_action(name),
            http_method="POST",
            http_path=f"/api/carina/tools/{name}",
            agent_schema="CarinaToolRegistry",
            runtime_handler=cls,
            actor_source="fail-closed user_id on tool callback",
            required_scope="tenant_tool_acl",
            risk="",
            approval="KeprixToolRiskRegistry / soft wall",
            idempotency="KeprixToolExecutionLedgerService",
            concurrency="tenant_scoped",
            audit_event="carina.tool.execute",
            tests="CarinaToolHttp* Pest",
            ui_equivalent="tenant UI module",
            rag_claim="native_chat_tool",
            current_status="engine_callback_path",
            sources=["CarinaToolRegistry", "AppServiceProvider"],
        )

    for name, cls in _php_tool_names(PROPRENEUR_ROOT / "app" / "Services" / "Carina" / "PlatformTools"):
        upsert(
            name,
            domain="platform",
            action=_infer_action(name),
            http_method="POST",
            http_path=f"/api/carina/tools/{name}",
            agent_schema="PlatformCarinaToolRegistry",
            runtime_handler=cls,
            actor_source="platform user",
            required_scope="platform_role",
            current_status="platform_callback_path",
            sources=["PlatformCarinaToolRegistry", "AppServiceProvider"],
        )

    for name in _config_tool_names(PROPRENEUR_ROOT / "config" / "carina_module_tools.php"):
        upsert(
            name,
            domain=_infer_domain(name),
            action=_infer_action(name),
            http_method="POST",
            http_path=f"/api/carina/tools/{name}",
            agent_schema="DefinedCarinaTool / carina_module_tools",
            runtime_handler="DefinedCarinaTool",
            actor_source="tenant user",
            current_status="engine_callback_path",
            sources=["config/carina_module_tools.php"],
        )

    for name in _config_tool_names(PROPRENEUR_ROOT / "config" / "aiva_v1_tools.php"):
        upsert(
            name,
            sources=["config/aiva_v1_tools.php"],
            agent_schema=rows.get(name, {}).get("agent_schema") or "aiva_v1_tools.php",
        )

    # Connector routes (infra ops, not domain CRUD)
    for route in connector.get("routes") or []:
        method = str(route.get("method") or "")
        path = str(route.get("path") or "")
        op_id = f"connector:{method}:{path}"
        upsert(
            op_id,
            domain="connector",
            action=str(route.get("purpose") or "route"),
            http_method=method,
            http_path=path,
            agent_schema="product_sidecar.connector",
            runtime_handler="product_http_connector",
            actor_source="sidecar token",
            approval="required" if route.get("approval_required") else "none",
            idempotency="yes" if route.get("idempotency") else "n/a",
            current_status="connector_allowlisted",
            sources=["_propreneur_connector"],
            notes="Connector allowlist only; PATCH/DELETE and /api/aiva/v1 CRUD not present (prompt 636).",
        )

    # HANDLERS inventory note (carina/aiva shared; none for propreneur nodes)
    for handler_key in sorted(HANDLERS.keys()):
        if handler_key.startswith(("crm.", "agent.", "soft_wall.", "memory.", "rag.", "playbook.", "jobs.", "channels.", "data.", "discovery.", "outreach.", "vical.", "booking.", "scout.", "ops.", "social.", "pack.")):
            upsert(
                f"shared_handler:{handler_key}",
                domain="shared_sidecar",
                action=handler_key,
                runtime_handler=handler_key,
                agent_schema="HANDLERS",
                current_status="carina_aiva_shared",
                sources=["handlers.HANDLERS"],
                notes="Shared product_sidecar handler; not a Propreneur pack node.",
            )

    operations = sorted(rows.values(), key=lambda r: r["operation_id"])
    pack_nodes = [r for r in operations if "pack_nodes" in (r.get("sources") or [])]
    live_pack = [r for r in pack_nodes if r.get("current_status") == "live"]
    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "prompt": "636-truth-baseline-and-fail-closed-status",
        "programme": "keprix-propreneur-crud-remediation",
        "mutation_behavior_widened": False,
        "counts": {
            "operations_total": len(operations),
            "pack_nodes": len(pack_nodes),
            "pack_nodes_live": len(live_pack),
            "pack_nodes_not_configured": sum(
                1 for r in pack_nodes if r.get("current_status") == "not_configured"
            ),
            "contract_tools": len(contract.get("tools") or []),
            "aiva_v1_generated": len(
                (json.loads(gen_path.read_text(encoding="utf-8")).get("tools") or [])
                if gen_path.is_file()
                else []
            ),
            "connector_routes": len(connector.get("routes") or []),
            "shared_handlers": len(HANDLERS),
            "behavioral_test_nodes": len(BEHAVIORAL_TEST_NODES),
        },
        "confirmed_gaps": [
            "Propreneur pack nodes have no HANDLERS entries; invoke would 501 if marked live.",
            "Fail-closed honesty now reports not_configured instead of live.",
            "Connector permits GET/POST only; no /api/aiva/v1 CRUD routes allowlisted.",
            "53-tool contract, 27 pack nodes, 35 Aiva v1 tools, and native Carina tools remain divergent sources.",
            "Engine connectivity (health, token, context, carina tools callback) is built; complete CRUD is under remediation.",
        ],
        "sources_inventoried": [
            "CarinaToolRegistry / PlatformCarinaToolRegistry (AppServiceProvider)",
            "config/carina_module_tools.php",
            "config/aiva_v1_tools.php",
            "docs/aiva/generated/aiva-v1-tools.json",
            "docs/aiva/openapi-aiva-v1.yaml",
            "routes/tenant.php (api/aiva/v1)",
            "keprix domain-packs/propreneur/contracts/propreneur-aiva-tools.v1.json",
            "product_sidecar packs/propreneur.py nodes",
            "product_sidecar registry _propreneur_connector",
            "product_sidecar handlers.HANDLERS",
            "AgentEngineFactory / Keprix bridge / approvals / events (documented in notes)",
        ],
        "operations": operations,
    }
    return summary


def main() -> int:
    report = build_report()
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(report, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    print(f"wrote {OUT_PATH}")
    print(json.dumps(report["counts"], indent=2))
    if report["counts"]["pack_nodes_live"] != 0:
        print("ERROR: pack nodes still labelled live", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
