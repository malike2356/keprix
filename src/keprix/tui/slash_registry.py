"""Local TUI slash commands (handled without backend fallthrough)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class LocalSlashCommand:
    names: tuple[str, ...]
    description: str


@dataclass(frozen=True)
class SlashCompletionItem:
    command: str
    description: str = ""


CommandSource = Literal["local", "backend", "skill", "plugin", "system"]
HandlerKind = Literal["local", "backend", "panel", "turn", "external"]


@dataclass(frozen=True)
class SlashCommandMetadata:
    name: str
    aliases: tuple[str, ...]
    description: str
    args: str
    examples: tuple[str, ...]
    source: CommandSource = "local"
    requires_session: bool = False
    danger_level: str = "safe"
    handler_kind: HandlerKind = "local"


LOCAL_SLASH_COMMANDS: tuple[LocalSlashCommand, ...] = (
    LocalSlashCommand(("/help", "/?"), "Show local and backend command help"),
    LocalSlashCommand(("/quit", "/exit", "/q"), "Exit the TUI"),
    LocalSlashCommand(("/new",), "Start a new chat"),
    LocalSlashCommand(("/sessions",), "Focus the session list"),
    LocalSlashCommand(("/model",), "Cycle the active model"),
    LocalSlashCommand(("/setup",), "Run full setup wizard"),
    LocalSlashCommand(("/busy",), "Show or set busy input mode"),
    LocalSlashCommand(("/steer",), "Inject guidance into the current turn"),
    LocalSlashCommand(("/interrupt", "/stop"), "Stop the current reply"),
    LocalSlashCommand(("/queue",), "Show queued messages"),
    LocalSlashCommand(("/clear",), "Clear the transcript"),
    LocalSlashCommand(("/copy",), "Copy the last agent reply"),
    LocalSlashCommand(("/reconnect",), "Reconnect to the backend"),
    LocalSlashCommand(("/details",), "Show or set details section visibility"),
    LocalSlashCommand(("/timeline",), "Show or hide the runtime event timeline"),
    LocalSlashCommand(("/voice",), "Enable or disable push-to-talk voice"),
    LocalSlashCommand(("/mouse",), "Toggle mouse capture at runtime"),
    LocalSlashCommand(("/compact",), "Compact the active transcript"),
    LocalSlashCommand(("/tools",), "Search available tools"),
    LocalSlashCommand(("/skills",), "Browse or manage skills"),
    LocalSlashCommand(("/plugins",), "Browse or manage plugins"),
    LocalSlashCommand(("/config",), "Show or edit configuration"),
    LocalSlashCommand(("/doctor",), "Run local diagnostics"),
    LocalSlashCommand(("/insights",), "Show session insights"),
    LocalSlashCommand(("/resume",), "Resume a previous session"),
    LocalSlashCommand(("/fork",), "Fork the active session"),
    LocalSlashCommand(("/theme",), "Change the active theme"),
    LocalSlashCommand(("/skin",), "Change the active skin"),
    LocalSlashCommand(("/export",), "Export session data"),
    LocalSlashCommand(("/import",), "Import session data"),
    LocalSlashCommand(("/feedback",), "Send product feedback"),
    LocalSlashCommand(("/debug",), "Toggle debug overlay"),
    LocalSlashCommand(("/open",), "Open a URL in the system browser"),
    LocalSlashCommand(
        ("/vault",),
        "Tenant Document Vault (list|search|mkdir|note|inspect|rename|trash|restore|export|sync|host)",
    ),
    LocalSlashCommand(("/search",), "Search the current transcript"),
    LocalSlashCommand(("/profile",), "Switch or inspect profile"),
    LocalSlashCommand(("/cron",), "Manage scheduled jobs"),
    LocalSlashCommand(("/gateway",), "Inspect gateway connection"),
    LocalSlashCommand(("/agent",), "Inspect sub-agents"),
    LocalSlashCommand(("/mcp",), "Manage MCP servers"),
    LocalSlashCommand(("/hub",), "Open the hub"),
    LocalSlashCommand(("/billing",), "Show billing state"),
    LocalSlashCommand(("/usage",), "Show usage counters"),
    LocalSlashCommand(("/status",), "Show system status"),
    LocalSlashCommand(("/restart",), "Restart the current runtime"),
)


COMMAND_OVERRIDES: dict[str, dict[str, object]] = {
    "/open": {"args": "<url>", "examples": ("/open https://example.com",), "handler_kind": "external"},
    "/vault": {
        "args": "list|search <q>|mkdir <name>|note <name>|inspect <id>|rename <id> <name>|trash <id>|restore <id>|export <id>|sync|host",
        "examples": ("/vault list", "/vault search invoice", "/vault mkdir Reports"),
        "handler_kind": "panel",
    },
    "/search": {"args": "<query>", "examples": ("/search invoice",), "handler_kind": "panel"},
    "/steer": {"args": "<instruction>", "examples": ("/steer focus on nginx",), "requires_session": True},
    "/busy": {"args": "interrupt|queue|steer", "examples": ("/busy queue",)},
    "/details": {"args": "[section mode]", "examples": ("/details all expanded",), "handler_kind": "panel"},
    "/timeline": {"args": "[hide]", "examples": ("/timeline", "/timeline hide"), "handler_kind": "panel"},
    "/model": {"args": "[query]", "examples": ("/model", "/model llama"), "handler_kind": "panel"},
    "/debug": {"handler_kind": "panel"},
    "/skills": {"handler_kind": "panel"},
    "/plugins": {"handler_kind": "panel"},
    "/sessions": {"handler_kind": "panel"},
    "/queue": {"handler_kind": "panel"},
    "/tools": {"source": "backend", "handler_kind": "backend", "requires_session": True},
    "/compact": {"source": "backend", "handler_kind": "backend", "requires_session": True},
    "/status": {"source": "backend", "handler_kind": "backend", "requires_session": True},
    "/billing": {"source": "backend", "handler_kind": "backend", "requires_session": True},
    "/usage": {"source": "backend", "handler_kind": "backend", "requires_session": True},
    "/restart": {"source": "backend", "handler_kind": "backend", "requires_session": True, "danger_level": "confirm"},
}


def local_command_names() -> set[str]:
    names: set[str] = set()
    for command in LOCAL_SLASH_COMMANDS:
        names.update(command.names)
    return names


def local_command_metadata() -> list[SlashCommandMetadata]:
    metadata: list[SlashCommandMetadata] = []
    for command in LOCAL_SLASH_COMMANDS:
        primary = command.names[0]
        overrides = COMMAND_OVERRIDES.get(primary, {})
        args = str(overrides.get("args") or "")
        examples = overrides.get("examples")
        if not isinstance(examples, tuple):
            examples = (primary,)
        metadata.append(
            SlashCommandMetadata(
                name=primary,
                aliases=command.names[1:],
                description=command.description,
                args=args,
                examples=examples,
                source=overrides.get("source", "local"),  # type: ignore[arg-type]
                requires_session=bool(overrides.get("requires_session", False)),
                danger_level=str(overrides.get("danger_level", "safe")),
                handler_kind=overrides.get("handler_kind", "local"),  # type: ignore[arg-type]
            )
        )
    return metadata


def slash_command_metadata(command_name: str) -> SlashCommandMetadata | None:
    cleaned = command_name.strip().split(maxsplit=1)[0].lower()
    for metadata in local_command_metadata():
        if cleaned == metadata.name or cleaned in metadata.aliases:
            return metadata
    return None


def is_local_slash_command(command: str | None) -> bool:
    if not command:
        return False
    return command.lower() in local_command_names()


def canonical_local_command(command: str | None) -> str | None:
    """Return the exact local slash command for an exact or unique fuzzy alias."""
    if not command:
        return None
    cleaned = command.strip().lower()
    if cleaned in local_command_names():
        return cleaned
    matches = local_completion_candidates(cleaned)
    if len(matches) == 1:
        return matches[0]
    return None


def local_completion_candidates(prefix: str) -> list[str]:
    return [item.command for item in local_completion_items(prefix)]


def local_completion_items(prefix: str) -> list[SlashCompletionItem]:
    cleaned = prefix.strip()
    if not cleaned.startswith("/"):
        return []
    needle = cleaned.lower()
    matches: list[SlashCompletionItem] = []
    seen: set[str] = set()
    for command in LOCAL_SLASH_COMMANDS:
        for name in command.names:
            if name.startswith(needle) or _fuzzy_match(needle.lstrip("/"), name.lstrip("/")):
                if name not in seen:
                    matches.append(SlashCompletionItem(command=name, description=command.description))
                    seen.add(name)
    return sorted(matches, key=lambda item: item.command)


def slash_command_description(command_name: str) -> str:
    metadata = slash_command_metadata(command_name)
    return metadata.description if metadata is not None else ""


def _fuzzy_match(needle: str, haystack: str) -> bool:
    if not needle:
        return True
    pos = 0
    for char in needle:
        pos = haystack.find(char, pos)
        if pos < 0:
            return False
        pos += 1
    return True
