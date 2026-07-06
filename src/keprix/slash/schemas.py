"""Slash command type definitions."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable


SlashHandler = Callable[["SlashContext"], Awaitable["SlashResult"]]


@dataclass
class SlashCommand:
    name: str
    aliases: list[str] = field(default_factory=list)
    description: str = ""
    usage: str = ""
    category: str = "general"
    min_role: str = "viewer"
    requires_confirmation: bool = False
    risk_level: str = "low"
    handler: SlashHandler | None = None
    cyber_scoped: bool = False


@dataclass
class SlashContext:
    user_id: str
    workspace_id: str
    channel: str
    channel_user_id: str
    raw_text: str
    command: str
    args: list[str] = field(default_factory=list)
    flags: dict[str, str] = field(default_factory=dict)
    json_args: dict[str, Any] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    request_id: str = ""
    role: str = "viewer"
    skip_confirmation: bool = False
    confirmation_token: str | None = None


@dataclass
class SlashResult:
    ok: bool
    message: str = ""
    blocks: list[dict[str, Any]] = field(default_factory=list)
    requires_confirmation: bool = False
    confirmation_token: str | None = None
    ephemeral: bool = False
    audit_id: str | None = None
    data: dict[str, Any] = field(default_factory=dict)


@dataclass
class ParsedSlash:
    command: str
    args: list[str]
    flags: dict[str, str]
    json_args: dict[str, Any] | None
    raw_text: str
    unknown: bool = False
    suggestions: list[str] = field(default_factory=list)
