"""Deny-by-default Customer Concierge tool policy (Prompt 630).

Authorization is enforced in code, not only in prompts. Prompt injection cannot
expand the allowlist.
"""

from __future__ import annotations

# Allowed visitor tools (Keprix + contract aliases)
CUSTOMER_CONCIERGE_ALLOWED_TOOLS: frozenset[str] = frozenset(
    {
        "clarify",
        "list_live_capabilities",
        # viCal / booking
        "vical-event-types-list",
        "vical-slots-offer",
        "vical-booking-create",
        "vical-booking-get",
        "vical-booking-cancel",
        "vical-booking-reschedule",
        "vical_slots",
        "vical_book",
        "vical_cancel",
        "vical_reschedule",
        # outreach booking aliases
        "outreach-booking-offer-slots",
        "outreach-booking-confirm",
        "outreach-booking-cancel",
        "outreach-booking-reschedule",
        # identity + knowledge + support (631 will flesh knowledge/support)
        "audience-contact-upsert",
        "audience_contact_upsert",
        "concierge-knowledge-search",
        "concierge_knowledge_search",
        "support-case-create",
        "support_case_create",
        "handoff-request",
        "handoff_request",
        "concierge-support-case-create",
        "concierge-handoff-request",
        "safe_reply",
    }
)

CUSTOMER_CONCIERGE_BLOCKED_TOOLS: frozenset[str] = frozenset(
    {
        "shell-exec",
        "shell_exec",
        "process",
        "file-write",
        "file_write",
        "file-delete",
        "file_delete",
        "file-read",
        "file_read",
        "http-request",
        "http_request",
        "memory",
        "session-search",
        "session_search",
        "worker-memory",
        "brain",
        "brain_graph",
        "brain-search",
        "document_vault_read",
        "document_vault_list",
        "document_vault_search",
        "vault_read",
        "vault_list",
        "cronjob",
        "send-message",
        "gmail-send",
        "admin",
        "billing",
        "outreach-leads-list",
        "outreach-leads-search",
        "crm_search",
        "crm-search",
        "crm_list",
    }
)

_BLOCKED_PREFIXES: tuple[str, ...] = (
    "workspace-",
    "workspace_",
    "propreneur",
    "billing",
    "vault",
    "shell",
    "admin",
    "document_vault",
    "document-vault",
    "brain",
    "fs_",
    "fs-",
    "file_",
    "file-",
)


def is_customer_concierge_tool_allowed(tool_name: str) -> bool:
    name = (tool_name or "").strip()
    if not name:
        return False
    if name in CUSTOMER_CONCIERGE_BLOCKED_TOOLS:
        return False
    lower = name.lower()
    for prefix in _BLOCKED_PREFIXES:
        if lower.startswith(prefix):
            return False
    if name in CUSTOMER_CONCIERGE_ALLOWED_TOOLS:
        return True
    return False


def assert_tool_allowed(tool_name: str) -> None:
    if not is_customer_concierge_tool_allowed(tool_name):
        raise PermissionError(f"audience_tool_denied:{tool_name}")
