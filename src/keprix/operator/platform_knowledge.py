"""Platform map helpers for the Keprix operator copilot."""

from __future__ import annotations

from typing import Any


def _normalise_terms(value: str) -> set[str]:
    import re

    return {term for term in re.findall(r"[a-z0-9]+", value.lower()) if len(term) > 2}


def installed_version() -> str:
    try:
        from keprix.upgrade.context import installed_keprix_version

        return installed_keprix_version()
    except Exception:
        return "unknown"


def list_navigation_items() -> list[dict[str, str]]:
    try:
        from keprix.ui_contract.navigation import NAV_GROUP_LABELS, NAV_ITEMS

        rows: list[dict[str, str]] = []
        for item in NAV_ITEMS:
            href = str(item.get("href") or "")
            if not href:
                continue
            group = str(item.get("group") or "")
            rows.append(
                {
                    "id": str(item.get("id") or ""),
                    "label": str(item.get("label") or item.get("id") or href),
                    "href": href,
                    "group": group,
                    "group_label": str(NAV_GROUP_LABELS.get(group) or group or "Other"),
                }
            )
        return rows
    except Exception:
        return []


def resolve_navigation_item(page_path: str | None) -> dict[str, str] | None:
    path = (page_path or "").strip() or "/"
    items = list_navigation_items()
    exact = next((item for item in items if item["href"] == path), None)
    if exact:
        return exact
    # Longest prefix match for nested routes (/settings/modules -> Modules)
    candidates = [
        item
        for item in items
        if path.startswith(item["href"].rstrip("/") + "/") or path.startswith(item["href"])
    ]
    if not candidates:
        return None
    candidates.sort(key=lambda item: len(item["href"]), reverse=True)
    return candidates[0]


def modules_summary() -> dict[str, Any]:
    try:
        from keprix.upgrade.gui_catalog import modules_payload

        payload = modules_payload()
        modules = payload.get("modules") or []
        return {
            "installed_version": payload.get("installed_version"),
            "counts": payload.get("counts") or {},
            "highlights": [
                {
                    "id": str(item.get("id") or ""),
                    "name": str(item.get("name") or ""),
                    "gui_status": str(item.get("gui_status") or ""),
                    "gui_href": item.get("gui_href"),
                    "category": str(item.get("category") or ""),
                }
                for item in modules
                if item.get("gui_status") == "available" and item.get("gui_href")
            ][:12],
            "missing_gui_count": len(payload.get("missing_gui") or []),
        }
    except Exception:
        return {"counts": {}, "highlights": [], "missing_gui_count": 0}


def search_live_module_catalog(query: str, *, limit: int = 8) -> list[dict[str, str]]:
    """Search the current module registry without relying on an indexed snapshot."""
    terms = _normalise_terms(query)
    if not terms:
        return []
    try:
        from keprix.upgrade.gui_catalog import list_gui_modules

        ranked: list[tuple[int, dict[str, str]]] = []
        for module in list_gui_modules():
            searchable = " ".join(
                (
                    str(module.id),
                    str(module.name),
                    str(module.description),
                    str(module.category),
                    str(module.gui_href or ""),
                )
            ).lower()
            score = sum(1 for term in terms if term in searchable)
            if score == 0:
                continue
            ranked.append(
                (
                    score,
                    {
                        "id": str(module.id),
                        "name": str(module.name),
                        "description": str(module.description)[:320],
                        "category": str(module.category),
                        "status": str(module.gui_status),
                        "route": str(module.gui_href or ""),
                        "source": "live:module-catalog",
                    },
                )
            )
        ranked.sort(key=lambda item: (-item[0], item[1]["name"].lower()))
        return [item[1] for item in ranked[:limit]]
    except Exception:
        return []


def live_platform_facts(query: str) -> dict[str, Any]:
    """Return authoritative, non-secret facts from registries loaded by this instance."""
    lowered = query.lower()
    module_matches = search_live_module_catalog(query)
    query_terms = _normalise_terms(query)
    named_module_match = any(
        query_terms.intersection(_normalise_terms(f"{item['id']} {item['name']}"))
        for item in module_matches
    )
    facts: dict[str, Any] = {
        "installed_version": installed_version(),
        "navigation_count": len(list_navigation_items()),
        "module_matches": module_matches,
        "source": "live:runtime-registries",
    }
    facts["version_requested"] = any(word in lowered for word in ("version", "release", "build"))
    facts["module_requested"] = named_module_match or any(
        word in lowered for word in ("module", "capability", "feature", "available", "support")
    )
    return facts


def readiness_summary() -> dict[str, Any]:
    try:
        from keprix.readiness.service import build_report

        report = build_report()
        failing = [
            {
                "id": check.id,
                "title": check.title,
                "status": check.status,
                "fix_path": check.fix_path or "",
            }
            for check in report.checks
            if check.status in {"fail", "warn"}
        ][:8]
        return {
            "overall": report.overall,
            "market": report.market,
            "upgrade": report.upgrade,
            "recovery": report.recovery,
            "counts": report.counts,
            "failing": failing,
        }
    except Exception:
        return {"overall": "unknown", "counts": {}, "failing": []}


def find_modules_for_path(page_path: str | None) -> list[dict[str, str]]:
    path = (page_path or "").strip()
    if not path:
        return []
    try:
        from keprix.upgrade.gui_catalog import list_gui_modules

        matches: list[dict[str, str]] = []
        for module in list_gui_modules():
            href = module.gui_href or ""
            if not href:
                continue
            if path == href or path.startswith(href.rstrip("/") + "/") or href.startswith(path):
                matches.append(
                    {
                        "id": module.id,
                        "name": module.name,
                        "gui_href": href,
                        "gui_status": module.gui_status,
                        "description": module.description[:200],
                    }
                )
        return matches[:6]
    except Exception:
        return []


def build_platform_map_markdown(*, page_path: str | None = None, page_label: str | None = None) -> str:
    version = installed_version()
    nav = list_navigation_items()
    modules = modules_summary()
    readiness = readiness_summary()
    current = resolve_navigation_item(page_path)
    module_hits = find_modules_for_path(page_path)

    groups: dict[str, list[str]] = {}
    for item in nav:
        groups.setdefault(item["group_label"], []).append(f"{item['label']} (`{item['href']}`)")

    lines = [
        "## Keprix platform map",
        "",
        f"- **Installed version:** {version}",
        f"- **Navigation surfaces:** {len(nav)}",
        f"- **Modules (available/partial/cli):** "
        f"{(modules.get('counts') or {}).get('available', 0)}/"
        f"{(modules.get('counts') or {}).get('partial', 0)}/"
        f"{(modules.get('counts') or {}).get('cli_api', 0)}",
        f"- **Readiness overall:** {readiness.get('overall', 'unknown')}",
        "",
    ]
    if page_path or page_label or current:
        label = page_label or (current or {}).get("label") or page_path or "/"
        href = page_path or (current or {}).get("href") or "/"
        group = (current or {}).get("group_label") or "Workspace"
        lines.extend(
            [
                "### Current page",
                f"- **Label:** {label}",
                f"- **Path:** `{href}`",
                f"- **Nav group:** {group}",
                "",
            ]
        )
        if module_hits:
            lines.append("Related modules:")
            for hit in module_hits:
                lines.append(f"- {hit['name']} (`{hit['gui_href']}`), status `{hit['gui_status']}`")
            lines.append("")

    lines.append("### Navigation groups")
    for group_label, entries in groups.items():
        preview = ", ".join(entries[:6])
        more = f" (+{len(entries) - 6} more)" if len(entries) > 6 else ""
        lines.append(f"- **{group_label}:** {preview}{more}")

    highlights = modules.get("highlights") or []
    if highlights:
        lines.append("")
        lines.append("### Highlight modules with GUI")
        for item in highlights[:8]:
            lines.append(f"- {item['name']} → `{item['gui_href']}`")

    failing = readiness.get("failing") or []
    if failing:
        lines.append("")
        lines.append("### Readiness attention")
        for check in failing:
            fix = f" Fix: `{check['fix_path']}`." if check.get("fix_path") else ""
            lines.append(f"- {check['title']} (`{check['status']}`).{fix}")

    lines.extend(
        [
            "",
            "### Operator help topics",
            "- Mutations / approvals: `/admin/mutations`, `/dashboard/mutation`",
            "- Playbooks: `/playbooks`",
            "- Channels / messaging: `/admin/channels`, `/settings/messaging`",
            "- Modules catalog: `/settings/modules`",
            "- Developer inventory: `/developer/module-inventory`",
            "- Readiness: `/admin/readiness`",
            "- Governance (Scout): `/settings/governance`",
            "- Billing: `/settings/billing`",
            "- Control Center: `/control-center`",
        ]
    )
    return "\n".join(lines).strip()


async def search_platform_knowledge(query: str, *, limit: int = 6) -> tuple[str, list[dict[str, Any]]]:
    """Retrieve self-knowledge RAG hits for platform questions. Never raises."""
    try:
        from keprix.memory.rag.self_knowledge import format_self_knowledge_context, retrieve_self_knowledge

        hits = await retrieve_self_knowledge(query, limit=limit, hybrid=True)
        return format_self_knowledge_context(hits, max_chars=4_500), hits
    except Exception:
        return "", []
