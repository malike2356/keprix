"""Gap audit: nav vs capability graph vs telegram toolset."""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from keprix.capability_mesh.dod import assert_dod, check_wired_telegram_nodes
from keprix.capability_mesh.graph import CapabilityGraph, load_graph

AuditClass = Literal["wired", "partial", "ui_only", "exception", "untracked"]


@dataclass
class AuditRow:
    nav_id: str
    label: str
    group: str
    graph_id: str | None
    status: AuditClass
    tools: list[str]
    telegram_claimed: bool
    tools_in_telegram: bool | None
    notes: str | None = None


def _telegram_tools() -> set[str]:
    from keprix.toolsets import _KEPRIX_CORE_TOOLS, resolve_toolset

    names = set(_KEPRIX_CORE_TOOLS)
    try:
        names.update(resolve_toolset("keprix-telegram"))
    except Exception:
        pass
    return names


def _nav_items() -> list[dict[str, Any]]:
    from keprix.ui_contract.navigation import NAV_ITEMS

    return list(NAV_ITEMS)


def classify_row(
    *,
    nav_id: str,
    label: str,
    group: str,
    graph: CapabilityGraph,
    telegram_tools: set[str],
) -> AuditRow:
    node = None
    for candidate in graph.nodes.values():
        if candidate.id == nav_id or candidate.nav_id == nav_id:
            node = candidate
            break

    if node is None:
        return AuditRow(
            nav_id=nav_id,
            label=label,
            group=group,
            graph_id=None,
            status="untracked",
            tools=[],
            telegram_claimed=False,
            tools_in_telegram=None,
            notes="No capability graph node",
        )

    surfaces = {s.lower() for s in node.channel_surfaces}
    telegram_claimed = "telegram" in surfaces
    tools_ok: bool | None = None
    if node.tools:
        tools_ok = all(t in telegram_tools for t in node.tools)
    elif telegram_claimed and node.status == "wired":
        tools_ok = False

    return AuditRow(
        nav_id=nav_id,
        label=label,
        group=group,
        graph_id=node.id,
        status=node.status,  # type: ignore[arg-type]
        tools=list(node.tools),
        telegram_claimed=telegram_claimed,
        tools_in_telegram=tools_ok,
        notes=node.notes,
    )


def run_audit(graph: CapabilityGraph | None = None) -> dict[str, Any]:
    graph = graph or load_graph()
    telegram_tools = _telegram_tools()
    rows = [
        classify_row(
            nav_id=str(item["id"]),
            label=str(item.get("label") or item["id"]),
            group=str(item.get("group") or ""),
            graph=graph,
            telegram_tools=telegram_tools,
        )
        for item in _nav_items()
    ]
    dod = assert_dod(graph)
    counts: dict[str, int] = {}
    for row in rows:
        counts[row.status] = counts.get(row.status, 0) + 1

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "counts": counts,
        "dod": dod,
        "rows": [asdict(r) for r in rows],
        "seed_nodes": sorted(graph.nodes.keys()),
        "wired_telegram_violations": [
            {"node_id": v.node_id, "code": v.code, "message": v.message}
            for v in check_wired_telegram_nodes(graph, platform_tools=telegram_tools)
        ],
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Capability mesh gap report",
        "",
        f"Generated: `{report['generated_at']}`",
        "",
        "Soft DoD: only `status=wired` + telegram must have tools in core/`keprix-telegram`.",
        "",
        "## Counts",
        "",
    ]
    for key, value in sorted((report.get("counts") or {}).items()):
        lines.append(f"- `{key}`: {value}")
    lines.extend(["", "## DoD (wired telegram)", ""])
    dod = report.get("dod") or {}
    lines.append(f"- ok: `{dod.get('ok')}`")
    lines.append(f"- violations: `{dod.get('violation_count')}`")
    for item in dod.get("violations") or []:
        lines.append(f"  - {item.get('message')}")

    lines.extend(
        [
            "",
            "## Seed graph nodes",
            "",
            ", ".join(f"`{n}`" for n in report.get("seed_nodes") or []),
            "",
            "## Nav rows (graph-tracked + untracked sample)",
            "",
            "| nav_id | status | telegram | tools_in_telegram | tools |",
            "| --- | --- | --- | --- | --- |",
        ]
    )

    # Prefer tracked + interesting; still include all for completeness but truncate tools col
    for row in report.get("rows") or []:
        tools = ", ".join(row.get("tools") or []) or "-"
        if len(tools) > 48:
            tools = tools[:45] + "..."
        lines.append(
            f"| `{row['nav_id']}` | `{row['status']}` | "
            f"{row['telegram_claimed']} | {row['tools_in_telegram']} | {tools} |"
        )

    lines.extend(
        [
            "",
            "## Regenerate",
            "",
            "```bash",
            "cd keprix && PYTHONPATH=src python3 -m keprix.capability_mesh audit --write",
            "```",
            "",
        ]
    )
    return "\n".join(lines)


def default_report_path() -> Path:
    # keprix/docs/architecture/...
    return Path(__file__).resolve().parents[3] / "docs" / "architecture" / "capability-mesh-gap-report.md"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit Keprix capability mesh gaps")
    parser.add_argument("--write", action="store_true", help="Write markdown report to docs/architecture")
    parser.add_argument("--path", type=str, default="", help="Optional output path")
    parser.add_argument("--json", action="store_true", help="Print JSON to stdout")
    args = parser.parse_args(argv)

    report = run_audit()
    if args.json:
        import json

        print(json.dumps(report, indent=2))
    else:
        print(render_markdown(report))

    if args.write:
        out = Path(args.path) if args.path else default_report_path()
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(render_markdown(report), encoding="utf-8")
        print(f"wrote {out}", flush=True)

    return 0 if report["dod"]["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
