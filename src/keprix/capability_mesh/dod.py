"""Feature Definition of Done checks for capability mesh (soft gate)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from keprix.capability_mesh.graph import CapabilityGraph, load_graph


@dataclass
class DodViolation:
    node_id: str
    code: str
    message: str


def _core_and_telegram_tools() -> set[str]:
    from keprix.toolsets import _KEPRIX_CORE_TOOLS, resolve_toolset

    names = set(_KEPRIX_CORE_TOOLS)
    try:
        names.update(resolve_toolset("keprix-telegram"))
    except Exception:
        pass
    return names


def check_wired_telegram_nodes(
    graph: CapabilityGraph | None = None,
    *,
    platform_tools: set[str] | None = None,
) -> list[DodViolation]:
    """
    Soft DoD: nodes marked ``wired`` that claim Telegram must list tools that
    appear in core / keprix-telegram. Partial/ui_only gaps are reported by audit,
    not hard-failed here.
    """
    graph = graph or load_graph()
    platform_tools = platform_tools if platform_tools is not None else _core_and_telegram_tools()
    violations: list[DodViolation] = []

    for node in graph.nodes.values():
        if node.status != "wired":
            continue
        surfaces = {s.lower() for s in node.channel_surfaces}
        if "telegram" not in surfaces:
            continue
        if not node.tools:
            violations.append(
                DodViolation(
                    node.id,
                    "wired_without_tools",
                    f"wired node {node.id} claims telegram but lists no tools",
                )
            )
            continue
        for tool in node.tools:
            if tool not in platform_tools:
                violations.append(
                    DodViolation(
                        node.id,
                        "tool_not_in_telegram_toolset",
                        f"wired node {node.id} tool {tool!r} missing from keprix-telegram/core",
                    )
                )
    return violations


def assert_dod(graph: CapabilityGraph | None = None) -> dict[str, Any]:
    violations = check_wired_telegram_nodes(graph)
    return {
        "ok": not violations,
        "violation_count": len(violations),
        "violations": [
            {"node_id": v.node_id, "code": v.code, "message": v.message} for v in violations
        ],
    }


FEATURE_DOD_CHECKLIST = [
    "Domain service / API exists",
    "UI if human-facing",
    "Agent tool(s) registered via tools.registry",
    "In _KEPRIX_CORE_TOOLS (or documented opt-in) for Telegram default",
    "Capability graph node + edges with via_id_field",
    "Discovery / self-knowledge note",
    "Tests + channel smoke note",
]

MESH_PROMPT_TEMPLATE = """
## Mesh DoD

- [ ] Domain service / API
- [ ] UI (if human-facing)
- [ ] Agent tools registered
- [ ] Core / keprix-telegram membership (or documented exception)
- [ ] Graph node + edges (`via_id_field`)
- [ ] agent-surface-access / capability-mesh note
- [ ] Tests + Telegram smoke
""".strip()
