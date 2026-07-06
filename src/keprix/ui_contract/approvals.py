"""Approval card field contract."""

from __future__ import annotations

from typing import Any

APPROVAL_CARD_FIELDS: list[str] = [
    "action",
    "requester",
    "target",
    "data_touched",
    "cost_impact",
    "risk_level",
    "reversible",
    "expires_at",
    "approve_action",
    "reject_action",
    "details_href",
    "audit_href",
]

RISK_LEVELS: list[str] = ["low", "medium", "high", "critical"]


def approval_card_template() -> dict[str, Any]:
    return {
        "fields": APPROVAL_CARD_FIELDS,
        "risk_levels": RISK_LEVELS,
        "actions": {"approve": "approval.approve", "reject": "approval.reject"},
    }
