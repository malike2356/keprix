"""Navigation tree architecture for Keprix agent OS.

Defines the canonical route structure, surface resolution rules,
and role-based visibility for every user-facing screen.

Surface resolution:
  keprix native    -> full nav + admin layer visible to workspace owner
  aiva surface     -> full nav scoped to aiva product, no admin layer
  abbis surface    -> full nav scoped to abbis product, no admin layer
  petraclus surface -> full nav scoped to petraclus product, no admin layer
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class NavRoute:
    """A single entry in the navigation tree."""
    id: str
    path: str
    label: str
    icon: str
    operator_only: bool = False
    children: list["NavRoute"] = field(default_factory=list)
    hidden_from_surfaces: list[str] = field(default_factory=list)


NAV_TREE: list[NavRoute] = [
    NavRoute("home", "/", "Home", "home"),
    NavRoute("sessions", "/sessions", "Sessions", "chat",
             children=[
                 NavRoute("session_detail", "/sessions/{id}", "Session", "chat"),
             ]),
    NavRoute("brain", "/brain", "Brain", "hub",
             children=[
                 NavRoute("brain_graph", "/brain/graph", "Graph", "share"),
                 NavRoute("brain_health", "/brain/health", "Health", "monitor_heart"),
                 NavRoute("brain_replay", "/brain/replay/{sessionId}", "Replay", "replay"),
                 NavRoute("brain_share", "/brain/share/{shareId}", "Shared view", "public"),
             ]),
    NavRoute("skills", "/skills", "Skills", "extension",
             children=[
                 NavRoute("skill_detail", "/skills/{id}", "Skill", "extension"),
             ]),
    NavRoute("tasks", "/tasks", "Tasks", "task_alt",
             children=[
                 NavRoute("task_detail", "/tasks/{id}", "Task", "task_alt"),
                 NavRoute("playbook_builder", "/tasks/playbooks/{id}", "Playbook builder", "schema"),
             ]),
    NavRoute("tools", "/tools", "Tools", "build",
             children=[
                 NavRoute("tool_detail", "/tools/{id}", "Tool", "build"),
             ]),
    NavRoute("voice", "/voice", "Voice", "phone",
             children=[
                 NavRoute("call_log", "/voice/calls", "Call log", "call_log"),
             ]),
    NavRoute("settings", "/settings", "Settings", "settings",
             children=[
                 NavRoute("settings_general", "/settings/general", "General", "tune"),
                 NavRoute("settings_voice", "/settings/voice", "Voice", "phone"),
                 NavRoute("settings_channels", "/settings/channels", "Channels", "hub"),
                 NavRoute("settings_api_keys", "/settings/api-keys", "API Keys", "key"),
                 NavRoute("settings_billing", "/settings/billing", "Billing", "payments"),
             ]),
    NavRoute("admin", "/admin", "Admin", "admin_panel_settings",
             operator_only=True,
             hidden_from_surfaces=["aiva", "abbis", "petraclus"],
             children=[
                 NavRoute("admin_products", "/admin/products", "Products", "category"),
                 NavRoute("admin_product_detail", "/admin/products/{id}", "Product", "category"),
                 NavRoute("admin_tool_acl", "/admin/tool-acl", "Tool ACL", "security"),
                 NavRoute("admin_network_egress", "/admin/network-egress", "Network Egress", "router"),
                 NavRoute("admin_quotas", "/admin/quotas", "Quotas", "speed"),
                 NavRoute("admin_isolation_audit", "/admin/isolation-audit", "Isolation Audit", "verified_user"),
             ]),
]

_ALL_ROUTES: dict[str, NavRoute] = {}


def _index_routes(routes: list[NavRoute]) -> None:
    for route in routes:
        _ALL_ROUTES[route.id] = route
        _index_routes(route.children)


_index_routes(NAV_TREE)


def get_route(route_id: str) -> NavRoute | None:
    return _ALL_ROUTES.get(route_id)


def top_level_for_surface(surface: str) -> list[NavRoute]:
    """Return top-level nav items visible on the given surface."""
    return [
        r for r in NAV_TREE
        if surface not in r.hidden_from_surfaces
    ]


def top_level_for_role(role: str) -> list[NavRoute]:
    """Return top-level nav items visible for the given role.

    Operators (role='admin' or 'owner') see the admin section.
    Regular users do not.
    """
    is_operator = role in ("admin", "owner")
    return [
        r for r in NAV_TREE
        if not r.operator_only or is_operator
    ]


def all_paths() -> list[str]:
    """Return a flat list of every path in the tree."""
    paths = []

    def _collect(routes: list[NavRoute]) -> None:
        for r in routes:
            paths.append(r.path)
            _collect(r.children)

    _collect(NAV_TREE)
    return paths


def to_dict(route: NavRoute) -> dict[str, Any]:
    return {
        "id": route.id,
        "path": route.path,
        "label": route.label,
        "icon": route.icon,
        "operator_only": route.operator_only,
        "children": [to_dict(c) for c in route.children],
    }
