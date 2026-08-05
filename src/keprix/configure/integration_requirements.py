"""Integration requirements for conversational config (Notion, Trello, GWS, webhooks)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class IntegrationField:
    key: str
    label: str
    description: str
    sensitive: bool
    optional: bool = False
    example: str | None = None
    env_key: str | None = None


@dataclass(frozen=True)
class IntegrationRequirement:
    id: str
    name: str
    aliases: tuple[str, ...]
    description: str
    fields: tuple[IntegrationField, ...]
    flow: str = "token"  # token | oauth | webhook
    setup_docs: str | None = None


INTEGRATION_REQUIREMENTS: tuple[IntegrationRequirement, ...] = (
    IntegrationRequirement(
        id="notion",
        name="Notion",
        aliases=("notion",),
        description="Notion integration token for workspace search and pages.",
        flow="token",
        fields=(
            IntegrationField(
                key="integration_token",
                label="Notion integration token",
                description="Internal integration secret from Notion developers.",
                sensitive=True,
                env_key="NOTION_INTEGRATION_TOKEN",
            ),
        ),
    ),
    IntegrationRequirement(
        id="trello",
        name="Trello",
        aliases=("trello",),
        description="Trello API key + token for boards and cards.",
        flow="token",
        fields=(
            IntegrationField(
                key="api_key",
                label="Trello API key",
                description="Trello Power-Up / API key.",
                sensitive=True,
                env_key="TRELLO_API_KEY",
            ),
            IntegrationField(
                key="token",
                label="Trello token",
                description="User token authorized for the API key.",
                sensitive=True,
                env_key="TRELLO_TOKEN",
            ),
        ),
    ),
    IntegrationRequirement(
        id="google_workspace",
        name="Google Workspace",
        aliases=("google workspace", "gws", "google calendar", "calendar", "gmail", "google drive"),
        description="Google Workspace OAuth for Calendar, Gmail, Drive, Sheets.",
        flow="oauth",
        fields=(
            IntegrationField(
                key="credentials_path",
                label="OAuth credentials path",
                description="Path to Google OAuth client JSON (optional if already set).",
                sensitive=False,
                optional=True,
                env_key="GOOGLE_WORKSPACE_CREDENTIALS_PATH",
            ),
            IntegrationField(
                key="oauth_code",
                label="OAuth code",
                description="Authorization code from the Google consent URL.",
                sensitive=True,
                optional=True,
            ),
        ),
    ),
    IntegrationRequirement(
        id="webhooks",
        name="Outbound webhooks",
        aliases=("webhook", "webhooks", "outbound webhook"),
        description="Developer outbound webhooks (URL + events).",
        flow="webhook",
        fields=(
            IntegrationField(
                key="url",
                label="Webhook URL",
                description="HTTPS endpoint that receives signed events.",
                sensitive=False,
                example="https://example.com/hooks/keprix",
            ),
            IntegrationField(
                key="events",
                label="Events",
                description="Comma-separated event names (default chat.completed).",
                sensitive=False,
                optional=True,
                example="chat.completed",
            ),
            IntegrationField(
                key="workspace_id",
                label="Workspace id",
                description="Workspace scope (default default).",
                sensitive=False,
                optional=True,
                example="default",
            ),
        ),
    ),
    IntegrationRequirement(
        id="companies_house",
        name="Companies House",
        aliases=("companies house", "companies-house", "ch", "uk company registry"),
        description="UK Companies House Public Data API for company search and profiles.",
        flow="token",
        setup_docs="https://developer.company-information.service.gov.uk/",
        fields=(
            IntegrationField(
                key="api_key",
                label="Companies House API key",
                description="API key from the Companies House Developer Hub (Basic auth username).",
                sensitive=True,
                env_key="COMPANIES_HOUSE_API_KEY",
                example="",
            ),
        ),
    ),
)

_BY_ID = {i.id: i for i in INTEGRATION_REQUIREMENTS}


def _norm(value: str) -> str:
    return " ".join(value.strip().lower().replace("_", " ").replace("-", " ").split())


_ALIAS: dict[str, IntegrationRequirement] = {}
for _item in INTEGRATION_REQUIREMENTS:
    _ALIAS[_norm(_item.id)] = _item
    _ALIAS[_norm(_item.name)] = _item
    for _a in _item.aliases:
        _ALIAS[_norm(_a)] = _item


def find_integration(value: str) -> IntegrationRequirement | None:
    if not value or not str(value).strip():
        return None
    return _ALIAS.get(_norm(str(value)))


def get_integration(integration_id: str) -> IntegrationRequirement | None:
    return _BY_ID.get((integration_id or "").strip().lower()) or find_integration(integration_id or "")


def list_integration_summaries() -> list[dict[str, object]]:
    return [
        {"id": i.id, "name": i.name, "aliases": list(i.aliases), "flow": i.flow}
        for i in INTEGRATION_REQUIREMENTS
    ]


def get_sensitive_integration_field_keys() -> set[str]:
    keys = {"integration_token", "token", "api_key", "oauth_code", "signing_secret"}
    for item in INTEGRATION_REQUIREMENTS:
        for fld in item.fields:
            if fld.sensitive:
                keys.add(fld.key)
                keys.add(fld.label.lower())
                if fld.env_key:
                    keys.add(fld.env_key)
    return keys
