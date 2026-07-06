"""Growth Loop playbook for the Opportunity Engine."""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

from keprix.opportunity.approvals import request_approval
from keprix.opportunity.integrations import IntegrationReport, discover_integrations
from keprix.opportunity.playbooks.offer_doc_generator import (
    CanonicalOfferDoc,
    build_canonical_offer_from_meta,
)
from keprix.opportunity.safety import run_content_safety_checks
from keprix.opportunity.workspace import read_artifact, read_opportunity_json, update_opportunity_json, write_artifact

_TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"

METRIC_NAMES: list[str] = [
    "Visits",
    "Conversion rate",
    "Lead count",
    "Cost per lead",
    "Reply rate",
    "Booked calls",
    "Show-up rate",
    "Close rate",
    "Revenue",
    "Refunds",
    "Churn",
    "Sales cycle length",
]

_SENSITIVE_INFERENCE_RE = re.compile(
    r"\b(infer (age|gender|ethnicity|religion|health|disability)|"
    r"target by (race|religion|health status)|deceptive targeting)\b",
    re.I,
)
_DECEPTIVE_TARGETING_RE = re.compile(
    r"\b(scrape personal|hidden targeting|bait.and.switch|fake urgency)\b",
    re.I,
)


class GrowthMetric(BaseModel):
    name: str
    value: str = "n/a"
    source: str = "manual"
    trend: str = "unknown"
    notes: str = ""


class GrowthExperiment(BaseModel):
    hypothesis: str
    asset_to_change: str
    expected_impact: str
    risk: Literal["low", "medium", "high"] = "medium"
    effort: Literal["low", "medium", "high"] = "medium"
    metric_to_watch: str
    approval_required: bool = True
    approval_action: str = ""
    rank_score: float = 0.0


class GrowthLoopInput(BaseModel):
    performance_data: dict[str, Any] = Field(default_factory=dict)
    manual_metrics: dict[str, str] = Field(default_factory=dict)


class GrowthLoopResult(BaseModel):
    report_md: str
    metrics: list[GrowthMetric]
    experiments: list[GrowthExperiment]
    approvals_requested: list[str] = Field(default_factory=list)
    manual_import_required: bool = False


def _template(name: str) -> str:
    return (_TEMPLATES_DIR / name).read_text(encoding="utf-8")


def _bullet_lines(items: list[str]) -> str:
    if not items:
        return "- None documented"
    return "\n".join(f"- {item}" for item in items)


def _resolve_doc(meta: dict[str, Any]) -> CanonicalOfferDoc:
    if meta.get("canonical_offer"):
        return CanonicalOfferDoc(**meta["canonical_offer"])
    return build_canonical_offer_from_meta(meta)


def _read_optional(opportunity_id: str, filename: str) -> str:
    try:
        return read_artifact(opportunity_id, filename)
    except FileNotFoundError:
        return ""


def build_manual_import_template() -> str:
    rows = "\n".join(
        f"| {name} |  | manual import |  |  |"
        for name in METRIC_NAMES
    )
    return (
        "Use this table when integrations are not connected. "
        "Paste weekly values from analytics, CRM, email, ads, forms, and Stripe exports.\n\n"
        "| Metric | Value | Source | Trend | Notes |\n"
        "| ------ | ----- | ------ | ----- | ----- |\n"
        f"{rows}\n"
    )


def _metric_from_sources(
    name: str,
    *,
    integration_report: IntegrationReport,
    performance_data: dict[str, Any],
    manual_metrics: dict[str, str],
) -> GrowthMetric:
    key = name.lower().replace(" ", "_")
    if key in manual_metrics:
        return GrowthMetric(
            name=name,
            value=manual_metrics[key],
            source="manual import",
            trend="n/a",
            notes="Operator supplied",
        )
    if key in performance_data:
        row = performance_data[key]
        if isinstance(row, dict):
            return GrowthMetric(name=name, **row)
        return GrowthMetric(name=name, value=str(row), source="performance_data")

    source_map = {
        "visits": "analytics",
        "conversion_rate": "analytics",
        "lead_count": "forms",
        "cost_per_lead": "ads",
        "reply_rate": "email",
        "booked_calls": "calendar",
        "show_up_rate": "calendar",
        "close_rate": "crm",
        "revenue": "stripe",
        "refunds": "stripe",
        "churn": "crm",
        "sales_cycle_length": "crm",
    }
    connector = source_map.get(key, "manual")
    connected = any(row.kind == connector for row in integration_report.connected)
    if connected and key in performance_data:
        return GrowthMetric(name=name, value=str(performance_data[key]), source=connector, trend="flat")

    if connected:
        return GrowthMetric(
            name=name,
            value="pending sync",
            source=connector,
            trend="unknown",
            notes="Connector available; awaiting first sync",
        )
    return GrowthMetric(
        name=name,
        value="n/a",
        source="manual import required",
        trend="unknown",
        notes=f"Connect {connector} or import manually",
    )


def collect_metrics(
    *,
    integration_report: IntegrationReport,
    performance_data: dict[str, Any],
    manual_metrics: dict[str, str],
) -> tuple[list[GrowthMetric], bool]:
    metrics = [
        _metric_from_sources(
            name,
            integration_report=integration_report,
            performance_data=performance_data,
            manual_metrics=manual_metrics,
        )
        for name in METRIC_NAMES
    ]
    manual_required = any(row.source == "manual import required" for row in metrics)
    return metrics, manual_required


def _effort_score(effort: str) -> float:
    return {"low": 3.0, "medium": 2.0, "high": 1.0}.get(effort, 1.0)


def _risk_penalty(risk: str) -> float:
    return {"low": 0.0, "medium": 0.5, "high": 1.0}.get(risk, 0.5)


def _impact_score(impact: str) -> float:
    lowered = impact.lower()
    if "high" in lowered:
        return 3.0
    if "medium" in lowered:
        return 2.0
    return 1.0


def rank_experiments(experiments: list[GrowthExperiment]) -> list[GrowthExperiment]:
    ranked: list[GrowthExperiment] = []
    for row in experiments:
        score = _impact_score(row.expected_impact) * _effort_score(row.effort) - _risk_penalty(row.risk)
        ranked.append(row.model_copy(update={"rank_score": round(score, 2)}))
    return sorted(ranked, key=lambda item: item.rank_score, reverse=True)


def suggest_experiments(*, doc: CanonicalOfferDoc, metrics: list[GrowthMetric]) -> list[GrowthExperiment]:
    weak_conversion = next((m for m in metrics if m.name == "Conversion rate" and m.value in {"n/a", "pending sync"}), None)
    weak_reply = next((m for m in metrics if m.name == "Reply rate"), None)

    experiments = [
        GrowthExperiment(
            hypothesis=f"Clarifying {doc.core_pain.lower()} in the hero will lift landing conversion",
            asset_to_change="assets/landing-page.md hero and problem sections",
            expected_impact="medium conversion lift",
            risk="low",
            effort="low",
            metric_to_watch="Conversion rate",
            approval_required=True,
            approval_action="publish_landing_page",
        ),
        GrowthExperiment(
            hypothesis="Email 1 subject line using exact ICP pain language will improve reply rate",
            asset_to_change="assets/email-nurture-sequence.md email 1 subject",
            expected_impact="medium reply rate lift",
            risk="medium",
            effort="low",
            metric_to_watch="Reply rate",
            approval_required=True,
            approval_action="send_email_sequence",
        ),
        GrowthExperiment(
            hypothesis="Top-performing ad hook becomes primary static ad concept",
            asset_to_change="assets/ad-copy.md static concepts",
            expected_impact="high CPL reduction",
            risk="medium",
            effort="medium",
            metric_to_watch="Cost per lead",
            approval_required=True,
            approval_action="create_ad",
        ),
        GrowthExperiment(
            hypothesis="CRM follow-up within 24h on booked calls improves show-up rate",
            asset_to_change="CRM launch pipeline stage automation",
            expected_impact="medium show-up lift",
            risk="medium",
            effort="medium",
            metric_to_watch="Show-up rate",
            approval_required=True,
            approval_action="update_crm",
        ),
        GrowthExperiment(
            hypothesis="Proof placeholder replaced with verified pilot quote improves close rate",
            asset_to_change="assets/sales-deck.md proof slide",
            expected_impact="high close rate lift",
            risk="low",
            effort="high",
            metric_to_watch="Close rate",
            approval_required=False,
            approval_action="",
        ),
    ]
    if weak_conversion:
        experiments[0].rank_score += 0.5
    if weak_reply and weak_reply.value in {"n/a", "pending sync", "0%"}:
        experiments[1].rank_score += 0.5
    return rank_experiments(experiments)


def validate_growth_guardrails(text: str) -> list[str]:
    violations: list[str] = []
    if re.search(r"\bincrease (ad )?budget\b", text, re.I) and "approval" not in text.lower():
        violations.append("Ad budget changes require explicit approval")
    if re.search(r"\b(rewrite|publish).*(live|production)\b", text, re.I) and "approval" not in text.lower():
        violations.append("Live page changes require explicit approval")
    if re.search(r"\b(contact|email) leads\b", text, re.I) and "approval" not in text.lower():
        violations.append("Lead contact requires explicit approval")
    if _SENSITIVE_INFERENCE_RE.search(text):
        violations.append("Sensitive attribute inference is not allowed")
    if _DECEPTIVE_TARGETING_RE.search(text):
        violations.append("Deceptive or harmful targeting is not allowed")
    return violations


def _metrics_table(metrics: list[GrowthMetric]) -> str:
    return "\n".join(
        f"| {row.name} | {row.value} | {row.source} | {row.trend} | {row.notes} |"
        for row in metrics
    )


def _format_experiment(index: int, row: GrowthExperiment) -> str:
    approval = row.approval_action or "none"
    return (
        f"### Experiment {index} (score {row.rank_score})\n"
        f"- Hypothesis: {row.hypothesis}\n"
        f"- Asset to change: {row.asset_to_change}\n"
        f"- Expected impact: {row.expected_impact}\n"
        f"- Risk: {row.risk}\n"
        f"- Effort: {row.effort}\n"
        f"- Metric to watch: {row.metric_to_watch}\n"
        f"- Approval required: {'yes' if row.approval_required else 'no'} ({approval})\n"
    )


def render_growth_loop_report(
    *,
    doc: CanonicalOfferDoc,
    meta: dict[str, Any],
    metrics: list[GrowthMetric],
    experiments: list[GrowthExperiment],
    integration_report: IntegrationReport,
    approval_summaries: list[str],
    manual_import_required: bool,
) -> str:
    launch_plan = str(meta.get("launch_plan") or {})
    status = meta.get("growth_status") or meta.get("status") or "monitoring"
    next_review = (datetime.now(timezone.utc) + timedelta(days=7)).date().isoformat()

    bottlenecks = _bullet_lines(
        [
            "Landing page conversion unknown without analytics sync",
            "Email reply rate needs nurture performance data",
            "Ad CPL depends on ads manager connection",
            f"Core pain to watch: {doc.core_pain}",
        ],
    )
    winning = _bullet_lines(
        [
            f"Positioning: {doc.positioning[:120]}",
            f"Mechanism message: {doc.unique_mechanism[:120]}",
            "Top ad hooks from assets/ad-copy.md (review manually if integrations missing)",
        ],
    )
    weak_assets = _bullet_lines(
        [
            "Proof placeholders in landing page and sales deck",
            "Unverified pricing claims if pricing artifact stale",
            "Social posts still in draft status",
        ],
    )
    ab_queue = "\n\n".join(_format_experiment(i + 1, row) for i, row in enumerate(experiments[:3]))
    budget = _bullet_lines(
        [
            "Hold ad budget steady until CPL baseline is imported",
            "Any budget increase requires approval (guardrail)",
            "Reallocate only after two weekly reviews with data",
        ],
    )
    crm_followups = _bullet_lines(
        [
            "Follow up booked calls within 24 hours",
            "Tag leads by ICP fit from 03-icp.md language",
            "Do not contact leads without approval",
        ],
    )

    replacements = {
        "{{current_status}}": (
            f"Monitoring {doc.offer_name} after launch planning. "
            f"Growth status: {status}. Connected integrations: {len(integration_report.connected)}."
        ),
        "{{metrics_table}}": _metrics_table(metrics),
        "{{manual_import}}": build_manual_import_template() if manual_import_required else "All metrics synced or manually supplied.",
        "{{funnel_bottlenecks}}": bottlenecks,
        "{{winning_messages}}": winning,
        "{{weak_assets}}": weak_assets,
        "{{recommended_experiments}}": "\n\n".join(
            _format_experiment(i + 1, row) for i, row in enumerate(experiments)
        ),
        "{{ab_test_queue}}": ab_queue,
        "{{budget_recommendations}}": budget,
        "{{crm_followups}}": crm_followups,
        "{{approval_requests}}": _bullet_lines(approval_summaries),
        "{{next_review_date}}": next_review,
    }
    body = _template("growth-loop-report.md")
    for key, value in replacements.items():
        body = body.replace(key, value)
    header = (
        f"# Growth Loop\n\n"
        f"Offer: {doc.offer_name}\n"
        f"Launch plan available: {'yes' if meta.get('launch_plan') or _read_optional(meta.get('opportunity_id', ''), '11-launch-plan.md') else 'partial'}\n\n"
    )
    return header + body


async def run_growth_loop_playbook(
    *,
    workspace_id: str,
    opportunity_id: str,
    request: GrowthLoopInput | None = None,
    requested_by: str = "system",
) -> GrowthLoopResult:
    request = request or GrowthLoopInput()
    meta = read_opportunity_json(opportunity_id)
    doc = _resolve_doc(meta)
    integration_report = discover_integrations(meta=meta)

    performance_data = dict(meta.get("performance_data") or {})
    performance_data.update(request.performance_data)
    manual_metrics = dict(meta.get("manual_metrics") or {})
    manual_metrics.update(request.manual_metrics)

    metrics, manual_import_required = collect_metrics(
        integration_report=integration_report,
        performance_data=performance_data,
        manual_metrics=manual_metrics,
    )
    experiments = suggest_experiments(doc=doc, metrics=metrics)

    approval_summaries: list[str] = []
    approvals_requested: list[str] = []
    for row in experiments:
        if not row.approval_required or not row.approval_action:
            continue
        approval = request_approval(
            workspace_id=workspace_id,
            opportunity_id=opportunity_id,
            action=row.approval_action,
            requested_by=requested_by,
            reason=f"Growth experiment: {row.hypothesis}",
            metadata={
                "preview": row.asset_to_change,
                "integration": row.approval_action,
                "risk_level": row.risk,
                "experiment_metric": row.metric_to_watch,
            },
        )
        approvals_requested.append(approval.approval_id)
        approval_summaries.append(
            f"{row.approval_action} for `{row.asset_to_change}` (risk {row.risk})",
        )

    report_md = render_growth_loop_report(
        doc=doc,
        meta={**meta, "opportunity_id": opportunity_id},
        metrics=metrics,
        experiments=experiments,
        integration_report=integration_report,
        approval_summaries=approval_summaries,
        manual_import_required=manual_import_required,
    )

    guardrail_violations = validate_growth_guardrails(report_md)
    if guardrail_violations:
        report_md += "\n\n## Guardrail Notes\n" + _bullet_lines(guardrail_violations) + "\n"

    run_content_safety_checks(opportunity_id=opportunity_id, text=report_md)
    write_artifact(opportunity_id, "14-growth-loop.md", report_md)

    update_opportunity_json(
        opportunity_id,
        {
            "phase": "growth_loop",
            "growth_status": "monitoring",
            "growth": {
                "last_review_at": datetime.now(timezone.utc).isoformat(),
                "next_review_date": (datetime.now(timezone.utc) + timedelta(days=7)).date().isoformat(),
                "metrics_snapshot": [row.model_dump() for row in metrics],
                "ranked_experiments": [row.model_dump() for row in experiments],
                "manual_import_required": manual_import_required,
                "approvals_requested": approvals_requested,
            },
        },
    )

    return GrowthLoopResult(
        report_md=report_md,
        metrics=metrics,
        experiments=experiments,
        approvals_requested=approvals_requested,
        manual_import_required=manual_import_required,
    )
