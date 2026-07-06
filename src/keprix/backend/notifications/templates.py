"""Notification message templates (Prompt 24)."""

from __future__ import annotations

from typing import Any

TEMPLATES: dict[str, dict[str, str]] = {
    "approval_needed": {
        "title": "Approval needed",
        "body": "{message}",
    },
    "job_complete": {
        "title": "Job complete",
        "body": "{message}",
    },
    "job_failed": {
        "title": "Job failed",
        "body": "{message}",
    },
    "scheduled_task_failed": {
        "title": "Scheduled task failed",
        "body": "{message}",
    },
    "setup_needs_attention": {
        "title": "Setup needs attention",
        "body": "{message}",
    },
    "credential_expiring": {
        "title": "Credential expiring",
        "body": "{message}",
    },
    "usage_limit_warning": {
        "title": "Usage limit warning",
        "body": "{message}",
    },
    "llm_budget_alert": {
        "title": "LLM spend approaching monthly budget",
        "body": "{message}",
    },
    "billing_failed": {
        "title": "Billing failed",
        "body": "{message}",
    },
    "subscription_changed": {
        "title": "Subscription changed",
        "body": "{message}",
    },
    "security_alert": {
        "title": "Security alert",
        "body": "{message}",
    },
    "governance_policy_alert": {
        "title": "Governance policy alert",
        "body": "{message}",
    },
    "data_import_complete": {
        "title": "Data import complete",
        "body": "{message}",
    },
    "research_complete": {
        "title": "Research complete",
        "body": "{message}",
    },
    "ml_experiment_complete": {
        "title": "ML experiment complete",
        "body": "{message}",
    },
    "pack_gate_pending": {
        "title": "Pack approval needed",
        "body": "{message}",
    },
    "localization_correction": {
        "title": "Localization correction submitted",
        "body": "{message}",
    },
}


def render_notification(notification_type: str, message: str, title: str | None = None) -> dict[str, str]:
    template = TEMPLATES.get(notification_type, {"title": title or "Notification", "body": "{message}"})
    return {
        "title": title or template["title"],
        "message": template["body"].format(message=message),
    }


def escalation_message(original: dict[str, Any]) -> str:
    return (
        f"Reminder: {original.get('title', 'Approval')} still needs attention. "
        f"{original.get('message', '')}"
    ).strip()
