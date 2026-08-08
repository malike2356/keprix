"""Visual CRM information architecture and design contract (prompt 506).

Four linked surfaces: pipeline board, workflow canvas, execution view, analytics.
Colour is never the only carrier of meaning; labels and shapes are required.
"""

from __future__ import annotations

from typing import Any

VISUAL_CONTRACT_VERSION = "1.0.0"

# Published route plan (Must)
VISUAL_ROUTES: dict[str, str] = {
    "overview": "/crm",
    "pipeline": "/crm/pipeline",
    "workflows": "/crm/workflows",
    "workflow_detail": "/crm/workflows/[id]",
    "run_detail": "/crm/runs/[id]",
    "analytics": "/crm/analytics",
    "ops": "/crm/ops",
}

NODE_FAMILIES: tuple[str, ...] = (
    "trigger",
    "discovery",
    "enrich",
    "decision",
    "approval",
    "wait",
    "outreach",
    "reply",
    "stage",
    "booking",
    "human_task",
    "integration",
    "goal",
    "stop",
    "error",
)

NODE_FAMILY_GROUPS: dict[str, tuple[str, ...]] = {
    "triggers": ("trigger",),
    "data": ("discovery", "enrich"),
    "decisions": ("decision",),
    "controls": ("wait", "stop"),
    "communications": ("outreach", "reply"),
    "human_work": ("approval", "human_task"),
    "integrations": ("integration", "booking"),
    "outcomes": ("stage", "goal"),
    "error_handling": ("error",),
}

RUNTIME_STATES: tuple[str, ...] = (
    "draft",
    "ready",
    "active",
    "waiting",
    "approval_required",
    "paused",
    "succeeded",
    "partially_succeeded",
    "failed",
    "cancelled",
    "suppressed",
    "skipped",
    "upcoming",
)

# Accessible state language: label + shape + icon key (colour secondary)
STATE_LEGEND: dict[str, dict[str, str]] = {
    "draft": {"label": "Draft", "shape": "dashed", "icon": "edit", "tone": "neutral"},
    "ready": {"label": "Ready", "shape": "outline", "icon": "ready", "tone": "info"},
    "active": {"label": "Active", "shape": "solid", "icon": "play", "tone": "info"},
    "waiting": {"label": "Waiting", "shape": "pulse-outline", "icon": "hourglass", "tone": "warning"},
    "approval_required": {
        "label": "Approval required",
        "shape": "shield",
        "icon": "shield",
        "tone": "warning",
    },
    "paused": {"label": "Paused", "shape": "outline", "icon": "pause", "tone": "neutral"},
    "succeeded": {"label": "Succeeded", "shape": "check", "icon": "check", "tone": "success"},
    "partially_succeeded": {
        "label": "Partially succeeded",
        "shape": "check-partial",
        "icon": "check_partial",
        "tone": "warning",
    },
    "failed": {"label": "Failed", "shape": "x", "icon": "error", "tone": "danger"},
    "cancelled": {"label": "Cancelled", "shape": "slash", "icon": "cancel", "tone": "neutral"},
    "suppressed": {"label": "Suppressed", "shape": "ban", "icon": "block", "tone": "danger"},
    "skipped": {"label": "Skipped", "shape": "dash", "icon": "skip", "tone": "neutral"},
    "upcoming": {"label": "Upcoming", "shape": "ghost", "icon": "next", "tone": "neutral"},
}

PERMISSIONS: tuple[str, ...] = (
    "view",
    "edit",
    "publish",
    "activate",
    "pause",
    "approve",
    "replay",
    "export",
    "dashboard_configure",
)

# Mobile may use ordered step view instead of miniature canvas
MOBILE_BEHAVIOUR: dict[str, str] = {
    "pipeline": "horizontal_lanes_or_stage_list",
    "workflow_canvas": "ordered_outline_editor",
    "execution": "static_timeline_table",
    "analytics": "critical_kpis_then_tables",
    "inspector": "bottom_sheet_with_back",
}

HARDENING_VISIBLE_STATES: tuple[str, ...] = (
    "workspace_isolation",
    "provenance",
    "audit",
    "idempotency",
    "contactability",
    "suppression",
    "kill_switch",
    "blocked",
    "waiting",
    "human_owned",
)

UI_VIEW_MODELS: dict[str, str] = {
    "pipeline_board": "GET /api/crm/visual/pipeline-board",
    "workflow_graph": "GET /api/crm/visual/workflows/{id}",
    "run_snapshot": "GET /api/crm/visual/runs/{id}",
    "run_events": "GET /api/crm/visual/runs/{id}/events",
    "metrics_query": "POST /api/crm/visual/metrics/query",
    "ops_centre": "GET /api/crm/visual/ops",
    "node_inspector": "GET /api/crm/visual/inspector",
}


def visual_contract_payload() -> dict[str, Any]:
    """Server view model for frontend IA without inventing browser-side semantics."""
    return {
        "version": VISUAL_CONTRACT_VERSION,
        "surfaces": {
            "pipeline_board": {
                "route": VISUAL_ROUTES["pipeline"],
                "question": "Where is each lead, contact, or deal now?",
                "view_model": UI_VIEW_MODELS["pipeline_board"],
            },
            "workflow_canvas": {
                "route": VISUAL_ROUTES["workflows"],
                "detail_route": VISUAL_ROUTES["workflow_detail"],
                "question": "What automation is configured to happen next?",
                "view_model": UI_VIEW_MODELS["workflow_graph"],
            },
            "execution_view": {
                "route": VISUAL_ROUTES["run_detail"],
                "question": "What is the agent doing or waiting for?",
                "view_model": UI_VIEW_MODELS["run_snapshot"],
            },
            "analytics_dashboard": {
                "route": VISUAL_ROUTES["analytics"],
                "question": "Are we producing safe business outcomes?",
                "view_model": UI_VIEW_MODELS["metrics_query"],
            },
        },
        "routes": VISUAL_ROUTES,
        "node_families": list(NODE_FAMILIES),
        "node_family_groups": {k: list(v) for k, v in NODE_FAMILY_GROUPS.items()},
        "runtime_states": list(RUNTIME_STATES),
        "state_legend": STATE_LEGEND,
        "permissions": list(PERMISSIONS),
        "mobile_behaviour": MOBILE_BEHAVIOUR,
        "hardening_visible_states": list(HARDENING_VISIBLE_STATES),
        "ui_view_models": UI_VIEW_MODELS,
        "navigation_links": [
            "lead",
            "list",
            "campaign",
            "workflow",
            "run",
            "activity",
            "approval",
            "booking",
            "source_evidence",
            "analytics_segment",
        ],
        "empty_states": ["empty", "loading", "partial", "blocked", "error", "permission_denied"],
        "notes": [
            "Reuse Keprix theme tokens and workspace shell.",
            "Do not invent a second permanent leads UI.",
            "Colour cannot be the only carrier of meaning.",
        ],
    }
