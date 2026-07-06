"""Setup item registry."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Awaitable


@dataclass(frozen=True)
class CredentialField:
    name: str
    label: str
    secret: bool = True
    required: bool = True


@dataclass
class SetupItem:
    id: str
    name: str
    category: str
    description: str
    required_role: str
    required_fields: list[CredentialField]
    optional_fields: list[CredentialField] = field(default_factory=list)
    enables_capabilities: list[str] = field(default_factory=list)
    confirmation_required: bool = False


SETUP_CATALOG: list[SetupItem] = [
    SetupItem(
        id="openai",
        name="OpenAI",
        category="llm",
        description="Connect OpenAI for chat and embeddings.",
        required_role="admin",
        required_fields=[CredentialField("api_key", "API key")],
        enables_capabilities=["llm.chat", "llm.embeddings"],
    ),
    SetupItem(
        id="anthropic",
        name="Anthropic",
        category="llm",
        description="Connect Anthropic Claude models.",
        required_role="admin",
        required_fields=[CredentialField("api_key", "API key")],
        enables_capabilities=["llm.chat"],
    ),
    SetupItem(
        id="telegram",
        name="Telegram",
        category="channel",
        description="Connect a Telegram bot.",
        required_role="admin",
        required_fields=[CredentialField("bot_token", "Bot token")],
        enables_capabilities=["channel.telegram"],
        confirmation_required=True,
    ),
    SetupItem(
        id="email",
        name="Email",
        category="email",
        description="Connect IMAP and SMTP mailbox credentials.",
        required_role="admin",
        required_fields=[
            CredentialField("username", "Username", secret=False),
            CredentialField("password", "Password"),
            CredentialField("imap_host", "IMAP host", secret=False),
            CredentialField("smtp_host", "SMTP host", secret=False),
        ],
        enables_capabilities=["email.inbox", "email.send"],
    ),
]


def get_catalog() -> list[dict[str, Any]]:
    return [
        {
            "id": item.id,
            "name": item.name,
            "category": item.category,
            "description": item.description,
            "required_role": item.required_role,
            "required_fields": [f.name for f in item.required_fields],
            "enables_capabilities": item.enables_capabilities,
            "confirmation_required": item.confirmation_required,
        }
        for item in SETUP_CATALOG
    ]


def get_item(service_id: str) -> SetupItem | None:
    for item in SETUP_CATALOG:
        if item.id == service_id:
            return item
    return None
