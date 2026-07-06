"""Assemble the full UI contract for clients."""

from __future__ import annotations

from typing import Any

from keprix.ui_contract.actions import ACTIONS
from keprix.ui_contract.approvals import approval_card_template
from keprix.ui_contract.empty_states import EMPTY_STATES
from keprix.ui_contract.errors import ERROR_TONE
from keprix.ui_contract.forms import FORM_FIELDS
from keprix.ui_contract.navigation import navigation_for_role
from keprix.ui_contract.schemas import UiContractResponse
from keprix.ui_contract.statuses import STATUS_VOCABULARY
from keprix.ui_contract.tables import TABLE_COLUMNS
from keprix.api.stt_config import stt_enabled
from keprix.governance.config import get_governance_config
from keprix.products.loader import get_product_feature_flags, load_products_config


def build_ui_contract(user: dict[str, Any] | None = None) -> dict[str, Any]:
    role = str((user or {}).get("role") or "user")
    username = str((user or {}).get("username") or "local")
    load_products_config()
    product_flags = get_product_feature_flags()
    payload = UiContractResponse(
        navigation=navigation_for_role(role),
        statuses=STATUS_VOCABULARY,
        actions=ACTIONS,
        approvals=approval_card_template(),
        empty_states=EMPTY_STATES,
        errors=ERROR_TONE,
        forms=FORM_FIELDS,
        tables=TABLE_COLUMNS,
        agent={
            "status": "ready",
            "label": "Agent ready",
            "current_job": None,
            "awaiting_approval": False,
        },
        workspace={
            "id": "default",
            "name": "Default workspace",
            "user": username,
            "role": role,
        },
        feature_flags={
            "commerce": False,
            "governance": bool(get_governance_config().get().get("enabled")),
            "data_workspace": True,
            "opportunity_engine": True,
            "voice_input": stt_enabled(),
            **product_flags,
        },
    )
    return payload.model_dump()
