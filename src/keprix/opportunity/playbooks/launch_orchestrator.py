"""Launch Orchestrator playbook for the Opportunity Engine."""

from __future__ import annotations

import secrets
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

from keprix.opportunity.approvals import (
    ACTION_RISK_LEVEL,
    check_action_allowed,
    is_risky_action,
    request_approval,
)
from keprix.opportunity.integrations import IntegrationReport, discover_integrations
from keprix.opportunity.playbooks.offer_doc_generator import (
    CanonicalOfferDoc,
    build_canonical_offer_from_meta,
    load_canonical_offer_doc,
)
from keprix.opportunity.safety import run_content_safety_checks
from keprix.opportunity.workspace import read_opportunity_json, update_opportunity_json, write_artifact

_TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"

RiskLevel = Literal["low", "medium", "high"]
ActionStatus = Literal[
    "dry_run",
    "pending_approval",
    "blocked",
    "pending_connector",
    "prepared",
    "executed",
]


class LaunchAction(BaseModel):
    action_id: str
    action: str
    integration: str
    risk_level: RiskLevel
    preview: str
    requires_approval: bool = True
    status: ActionStatus = "dry_run"
    result: str = ""


class LaunchPlanResult(BaseModel):
    opportunity_id: str
    dry_run: bool
    launch_plan_md: str
    actions: list[LaunchAction] = Field(default_factory=list)
    integration_report: IntegrationReport
    approvals_requested: list[str] = Field(default_factory=list)
    blocked_actions: list[str] = Field(default_factory=list)


class LaunchBlockedError(Exception):
    """Raised when a risky launch action is attempted without approval."""

    def __init__(self, action: LaunchAction, reason: str) -> None:
        self.action = action
        self.reason = reason
        super().__init__(reason)


def _template(name: str) -> str:
    return (_TEMPLATES_DIR / name).read_text(encoding="utf-8")


def _bullet_lines(items: list[str]) -> str:
    if not items:
        return "- None"
    return "\n".join(f"- {item}" for item in items)


def _resolve_doc(meta: dict[str, Any]) -> CanonicalOfferDoc:
    if meta.get("canonical_offer"):
        return CanonicalOfferDoc(**meta["canonical_offer"])
    return build_canonical_offer_from_meta(meta)


def build_planned_actions(
    *,
    doc: CanonicalOfferDoc,
    integration_report: IntegrationReport,
) -> list[LaunchAction]:
    connected = {row.kind for row in integration_report.connected}
    specs: list[tuple[str, str, str, str, RiskLevel]] = [
        ("update_crm", "crm", "Create launch pipeline stage and lifecycle mapping", "crm", "medium"),
        ("send_email_sequence", "email", "Schedule nurture sequence from assets/email-nurture-sequence.md", "email", "high"),
        ("publish_post", "social", "Queue LinkedIn posts from assets/linkedin-posts.md", "social", "high"),
        ("create_ad", "ads", "Create ad campaign from assets/ad-copy.md", "ads", "high"),
        ("set_ad_budget", "ads", "Set initial ad budget after campaign review", "ads", "high"),
        ("publish_landing_page", "website", "Publish landing page from assets/landing-page.md", "website", "high"),
        ("upload_lead_list", "crm", "Import warm lead list for launch cohort", "crm", "high"),
        ("create_stripe_product", "stripe", "Create Stripe product and price from 06-pricing.md", "stripe", "high"),
        ("charge_customer", "stripe", "Enable checkout after product approval", "stripe", "high"),
        ("send_outreach", "email", "Send approved outreach to ICP segment", "email", "high"),
    ]
    actions: list[LaunchAction] = []
    for action, integration, preview, connector_kind, risk in specs:
        requires_approval = is_risky_action(action)
        status: ActionStatus = "dry_run"
        result = ""
        if connector_kind not in connected:
            status = "pending_connector"
            result = f"Connector missing: complete setup for {connector_kind}"
        actions.append(
            LaunchAction(
                action_id="act-" + secrets.token_hex(3),
                action=action,
                integration=integration,
                risk_level=risk,
                preview=preview,
                requires_approval=requires_approval,
                status=status,
                result=result,
            ),
        )
    return actions


def render_rollback_plan(*, doc: CanonicalOfferDoc) -> str:
    return _bullet_lines(
        [
            "Pause all scheduled emails and outreach immediately",
            "Unpublish landing page and set maintenance notice",
            "Pause ad campaigns and zero budgets",
            "Revert CRM lifecycle stage to pre-launch",
            "Disable Stripe checkout links created for this launch",
            "Archive social posts queued for this opportunity",
            f"Document incident and learnings for {doc.offer_name}",
        ],
    )


def render_launch_plan_markdown(
    *,
    doc: CanonicalOfferDoc,
    meta: dict[str, Any],
    integration_report: IntegrationReport,
    actions: list[LaunchAction],
) -> str:
    goal = str(meta.get("goal") or doc.core_promise)
    approval_lines = [
        f"{row.action} ({row.risk_level}) via {row.integration}: {row.preview}"
        for row in actions
        if row.requires_approval
    ]
    connected = [
        f"{row.label} ({row.provider or 'connected'})" for row in integration_report.connected
    ]
    missing = [
        f"{row.label}: {row.setup_instructions}" for row in integration_report.missing
    ]
    checklist = _bullet_lines(
        [
            "Validation score reviewed",
            "Canonical offer doc approved",
            "Asset drafts reviewed (landing, email, ads, deck)",
            "Integrations connected or setup tasks assigned",
            "Rollback plan acknowledged",
            "Launch approval obtained",
        ],
    )

    def _section_for_connector(kind: str, connected_text: str, missing_text: str) -> str:
        if any(row.kind == kind for row in integration_report.connected):
            return connected_text
        task = next((t for t in integration_report.pending_tasks if t["integration"] == kind), None)
        if task:
            return f"Pending connector task: {task['instructions']}"
        return missing_text

    replacements = {
        "{{launch_goal}}": goal,
        "{{required_approvals}}": _bullet_lines(approval_lines),
        "{{connected_integrations}}": _bullet_lines(connected),
        "{{missing_integrations}}": _bullet_lines(missing),
        "{{pre_launch_checklist}}": checklist,
        "{{crm_setup}}": _section_for_connector(
            "crm",
            "Sync ICP segment and launch pipeline stage (approval required before lifecycle updates).",
            "Connect CRM before updating lifecycle stages.",
        ),
        "{{email_setup}}": _section_for_connector(
            "email",
            "Load draft nurture sequence; approval required before send.",
            "Connect email platform to schedule nurture sequence.",
        ),
        "{{social_plan}}": _section_for_connector(
            "social",
            "Queue posts from assets/linkedin-posts.md; approval required before publish.",
            "Connect social account to schedule posts.",
        ),
        "{{ads_plan}}": _section_for_connector(
            "ads",
            "Prepare campaigns from assets/ad-copy.md; approvals required for create and budget.",
            "Connect ads manager before campaign creation.",
        ),
        "{{landing_plan}}": _section_for_connector(
            "website",
            "Deploy assets/landing-page.md to staging then production after approval.",
            "Configure website or landing page builder deploy target.",
        ),
        "{{analytics_plan}}": _section_for_connector(
            "analytics",
            "Attach UTM plan and conversion events to landing page and ads.",
            "Connect analytics to measure launch funnel.",
        ),
        "{{stripe_plan}}": _section_for_connector(
            "stripe",
            "Create product and price drafts from pricing artifact; approval before checkout goes live.",
            "Connect Stripe before creating products or charging customers.",
        ),
        "{{rollback_plan}}": render_rollback_plan(doc=doc),
        "{{launch_approval}}": (
            "Launch execution is approval-led. Default mode is dry run. "
            "Obtain explicit approval for every high-risk action before execution."
        ),
    }
    body = _template("launch-plan-template.md")
    for key, value in replacements.items():
        body = body.replace(key, value)
    header = f"# Launch Plan\n\nOffer: {doc.offer_name}\nICP: {doc.primary_icp}\n\n"
    return header + body


def _integration_connected(report: IntegrationReport, kind: str) -> bool:
    return any(row.kind == kind for row in report.connected)


def execute_planned_actions(
    *,
    opportunity_id: str,
    actions: list[LaunchAction],
    dry_run: bool,
    integration_report: IntegrationReport,
    approved_actions: set[str] | None = None,
) -> tuple[list[LaunchAction], list[str]]:
    approved_actions = approved_actions or set()
    blocked: list[str] = []
    updated: list[LaunchAction] = []

    integration_for_action = {
        "update_crm": "crm",
        "upload_lead_list": "crm",
        "send_email_sequence": "email",
        "send_outreach": "email",
        "publish_post": "social",
        "create_ad": "ads",
        "set_ad_budget": "ads",
        "edit_ad": "ads",
        "publish_landing_page": "website",
        "create_stripe_product": "stripe",
        "charge_customer": "stripe",
    }

    for row in actions:
        current = row.model_copy()
        connector = integration_for_action.get(row.action, row.integration)
        if not _integration_connected(integration_report, connector):
            current.status = "pending_connector"
            current.result = f"Skipped: {connector} connector not configured"
            updated.append(current)
            continue

        if dry_run:
            current.status = "dry_run"
            current.result = "Dry run: action not executed"
            updated.append(current)
            continue

        allowed, reason = check_action_allowed(
            opportunity_id=opportunity_id,
            action=row.action,
            human_approved=row.action in approved_actions,
        )
        if row.requires_approval and not allowed:
            current.status = "blocked"
            current.result = reason or "Approval required"
            blocked.append(row.action_id)
            updated.append(current)
            continue

        current.status = "prepared"
        current.result = "Prepared for execution (connector available; approval satisfied if required)"
        updated.append(current)

    return updated, blocked


async def run_launch_plan(
    opportunity_id: str,
    *,
    dry_run: bool = True,
    workspace_id: str | None = None,
    requested_by: str = "system",
    approved_actions: list[str] | None = None,
) -> LaunchPlanResult:
    meta = read_opportunity_json(opportunity_id)
    workspace_id = workspace_id or str(meta.get("workspace_id") or "default")
    load_canonical_offer_doc(opportunity_id)
    doc = _resolve_doc(meta)

    integration_report = discover_integrations(meta=meta)
    actions = build_planned_actions(doc=doc, integration_report=integration_report)
    launch_plan_md = render_launch_plan_markdown(
        doc=doc,
        meta=meta,
        integration_report=integration_report,
        actions=actions,
    )
    run_content_safety_checks(opportunity_id=opportunity_id, text=launch_plan_md)

    approvals_requested: list[str] = []
    for row in actions:
        if not row.requires_approval:
            continue
        approval = request_approval(
            workspace_id=workspace_id,
            opportunity_id=opportunity_id,
            action=row.action,
            requested_by=requested_by,
            reason=row.preview,
            metadata={
                "preview": row.preview,
                "integration": row.integration,
                "risk_level": ACTION_RISK_LEVEL.get(row.action, row.risk_level),
                "launch_action_id": row.action_id,
            },
        )
        approvals_requested.append(approval.approval_id)

    executed_actions, blocked = execute_planned_actions(
        opportunity_id=opportunity_id,
        actions=actions,
        dry_run=dry_run,
        integration_report=integration_report,
        approved_actions=set(approved_actions or []),
    )

    if not dry_run and blocked:
        blocked_row = next(row for row in executed_actions if row.action_id in blocked)
        raise LaunchBlockedError(blocked_row, blocked_row.result or "Approval required")

    write_artifact(opportunity_id, "11-launch-plan.md", launch_plan_md)
    update_opportunity_json(
        opportunity_id,
        {
            "phase": "launch_orchestrator",
            "launch_plan": {
                "dry_run": dry_run,
                "actions": [row.model_dump() for row in executed_actions],
                "pending_connector_tasks": integration_report.pending_tasks,
                "approvals_requested": approvals_requested,
            },
            "status": "approval_required",
        },
    )

    return LaunchPlanResult(
        opportunity_id=opportunity_id,
        dry_run=dry_run,
        launch_plan_md=launch_plan_md,
        actions=executed_actions,
        integration_report=integration_report,
        approvals_requested=approvals_requested,
        blocked_actions=blocked,
    )


async def run_launch_orchestrator_playbook(
    *,
    workspace_id: str,
    opportunity_id: str,
    dry_run: bool = True,
    requested_by: str = "system",
) -> str:
    result = await run_launch_plan(
        opportunity_id,
        dry_run=dry_run,
        workspace_id=workspace_id,
        requested_by=requested_by,
    )
    return result.launch_plan_md
