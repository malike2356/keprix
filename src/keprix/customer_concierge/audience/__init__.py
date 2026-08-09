"""Audience principal package (Prompt 630)."""

from __future__ import annotations

from keprix.customer_concierge.audience.context import (
    AudiencePrincipalContext,
    clear_audience_context,
    gate_tool_for_current_audience,
    get_audience_context,
    set_audience_context,
)
from keprix.customer_concierge.audience.embed import (
    is_origin_allowed,
    new_embed_nonce,
    sign_widget_embed_config,
    verify_widget_embed_config,
)
from keprix.customer_concierge.audience.ingress import open_audience_session, resume_audience_session
from keprix.customer_concierge.audience.models import AudienceIdentity, AudienceSession
from keprix.customer_concierge.audience.store import get_audience_store, reset_audience_store_for_tests
from keprix.customer_concierge.audience.tool_policy import (
    CUSTOMER_CONCIERGE_ALLOWED_TOOLS,
    is_customer_concierge_tool_allowed,
)

__all__ = [
    "CUSTOMER_CONCIERGE_ALLOWED_TOOLS",
    "AudienceIdentity",
    "AudiencePrincipalContext",
    "AudienceSession",
    "clear_audience_context",
    "gate_tool_for_current_audience",
    "get_audience_context",
    "get_audience_store",
    "is_customer_concierge_tool_allowed",
    "is_origin_allowed",
    "new_embed_nonce",
    "open_audience_session",
    "reset_audience_store_for_tests",
    "resume_audience_session",
    "set_audience_context",
    "sign_widget_embed_config",
    "verify_widget_embed_config",
]
