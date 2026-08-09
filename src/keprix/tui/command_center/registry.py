"""Pure Command Center action registry."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from keprix.tui.client import ModelItem, RegistryItem, SessionItem
from keprix.tui.command_center.actions import CommandCenterAction, action_id
from keprix.tui.commands.registry import local_command_metadata
from keprix.tui.fuzzy_match import fuzzy_score
from keprix.tui.theme_system import available_themes


@dataclass
class CommandCenterRegistry:
    actions: dict[str, CommandCenterAction] = field(default_factory=dict)

    def add(self, action: CommandCenterAction) -> None:
        self.actions[action.id] = action

    def extend(self, actions: list[CommandCenterAction]) -> None:
        for action in actions:
            self.add(action)

    def get(self, action_id_value: str) -> CommandCenterAction | None:
        return self.actions.get(action_id_value)

    def all(self) -> list[CommandCenterAction]:
        return sorted(self.actions.values(), key=lambda action: (action.category, action.title, action.id))

    def search(self, query: str, *, limit: int = 20) -> list[CommandCenterAction]:
        cleaned = query.strip().lower()
        if not cleaned:
            return self.all()[:limit]
        scored = [
            (score, action)
            for action in self.actions.values()
            if (score := fuzzy_score(cleaned, action.search_text())) is not None
        ]
        return [action for _, action in sorted(scored, key=lambda item: (item[0], item[1].title, item[1].id))[:limit]]


def local_command_actions() -> list[CommandCenterAction]:
    actions: list[CommandCenterAction] = []
    for command in local_command_metadata():
        actions.append(
            CommandCenterAction(
                id=action_id("slash", command.name),
                title=command.name,
                description=command.description,
                kind="slash",
                effect="insert",
                value=command.name,
                category="Slash commands",
                keywords=(*command.aliases, command.args, command.source, command.handler_kind),
            )
        )
    return actions


def session_actions(sessions: list[SessionItem]) -> list[CommandCenterAction]:
    return [
        CommandCenterAction(
            id=action_id("session", session.id),
            title=session.title,
            description=session.preview or session.last_active or "Switch session",
            kind="session",
            effect="switch",
            value=session.id,
            category="Sessions",
            keywords=(session.id, session.last_active),
        )
        for session in sessions
    ]


def model_actions(models: list[ModelItem]) -> list[CommandCenterAction]:
    return [
        CommandCenterAction(
            id=action_id("model", model.id),
            title=model.name,
            description=f"{model.provider} {model.context_window} context".strip(),
            kind="model",
            effect="switch",
            value=model.id,
            category="Models",
            keywords=(model.provider, model.id),
        )
        for model in models
    ]


def registry_item_actions(items: list[RegistryItem], *, kind: str, category: str) -> list[CommandCenterAction]:
    return [
        CommandCenterAction(
            id=action_id(kind, item.name),
            title=item.name,
            description=item.description or item.source or category,
            kind=kind,  # type: ignore[arg-type]
            effect="open",
            value=item.name,
            category=category,
            keywords=(item.version, item.source, "enabled" if item.enabled else "disabled"),
            disabled=not item.enabled,
        )
        for item in items
    ]


def recent_file_actions(paths: list[str | Path]) -> list[CommandCenterAction]:
    actions: list[CommandCenterAction] = []
    for raw in paths:
        path = Path(raw)
        actions.append(
            CommandCenterAction(
                id=action_id("file", str(path)),
                title=path.name or str(path),
                description=str(path),
                kind="file",
                effect="open",
                value=str(path),
                category="Recent files",
                keywords=(str(path.parent),),
            )
        )
    return actions


def runtime_actions() -> list[CommandCenterAction]:
    return [
        CommandCenterAction("runtime:interrupt", "Interrupt turn", "Stop the current agent turn", "runtime", "execute", "interrupt", "Runtime"),
        CommandCenterAction("runtime:flush-queue", "Flush queue", "Send the next queued message", "runtime", "execute", "flush_queue", "Runtime"),
        CommandCenterAction("runtime:reconnect", "Reconnect", "Reconnect to the backend runtime", "runtime", "execute", "reconnect", "Runtime"),
        CommandCenterAction("ui:review", "Review last turn", "Open the compact last-turn report", "ui", "open", "review", "Review"),
        CommandCenterAction("ui:help", "Help", "Open keyboard and command help", "help", "open", "help", "Help"),
    ]


def document_vault_actions() -> list[CommandCenterAction]:
    """Tenant Document Vault workflows (never host filesystem)."""
    return [
        CommandCenterAction(
            id="vault:list",
            title="Vault: list root",
            description="List tenant Document Vault root (not host FS)",
            kind="vault",
            effect="execute",
            value="list",
            category="Document Vault",
            keywords=("documents", "files", "browse", "tenant"),
        ),
        CommandCenterAction(
            id="vault:search",
            title="Vault: search",
            description="Search tenant Document Vault; type query after selecting",
            kind="vault",
            effect="execute",
            value="search",
            category="Document Vault",
            keywords=("find", "query"),
        ),
        CommandCenterAction(
            id="vault:mkdir",
            title="Vault: create folder",
            description="Create a folder in the tenant Document Vault",
            kind="vault",
            effect="execute",
            value="mkdir",
            category="Document Vault",
            keywords=("folder", "create"),
        ),
        CommandCenterAction(
            id="vault:create-note",
            title="Vault: create note",
            description="Create a markdown note in the tenant Document Vault",
            kind="vault",
            effect="execute",
            value="create_note",
            category="Document Vault",
            keywords=("markdown", "text", "create"),
        ),
        CommandCenterAction(
            id="vault:inspect",
            title="Vault: inspect item",
            description="Read vault item content by id (tenant vault)",
            kind="vault",
            effect="execute",
            value="inspect",
            category="Document Vault",
            keywords=("read", "preview", "content"),
        ),
        CommandCenterAction(
            id="vault:rename",
            title="Vault: rename",
            description="Rename a vault item (id then new name)",
            kind="vault",
            effect="execute",
            value="rename",
            category="Document Vault",
            keywords=("move", "name"),
        ),
        CommandCenterAction(
            id="vault:trash",
            title="Vault: trash",
            description="Move a vault item to trash by id",
            kind="vault",
            effect="execute",
            value="trash",
            category="Document Vault",
            keywords=("delete", "remove"),
        ),
        CommandCenterAction(
            id="vault:restore",
            title="Vault: restore",
            description="Restore a trashed vault item by id",
            kind="vault",
            effect="execute",
            value="restore",
            category="Document Vault",
            keywords=("undelete"),
        ),
        CommandCenterAction(
            id="vault:export",
            title="Vault: export markdown",
            description="Export a vault item as markdown bytes summary",
            kind="vault",
            effect="execute",
            value="export",
            category="Document Vault",
            keywords=("download", "md"),
        ),
        CommandCenterAction(
            id="vault:sync-status",
            title="Vault: sync status",
            description="Show Drive sync status placeholder (full sync in 649)",
            kind="vault",
            effect="execute",
            value="sync_status",
            category="Document Vault",
            keywords=("drive", "google", "sync"),
        ),
        CommandCenterAction(
            id="vault:host-fs-note",
            title="Host FS note",
            description="Reminder: admin host filesystem is separate from Document Vault",
            kind="vault",
            effect="execute",
            value="host_fs_note",
            category="Document Vault",
            keywords=("admin", "filesystem", "host"),
        ),
    ]


def theme_actions() -> list[CommandCenterAction]:
    return [
        CommandCenterAction(
            id=action_id("theme", name),
            title=name,
            description="Switch TUI theme",
            kind="ui",
            effect="switch",
            value=name,
            category="Themes",
            keywords=("theme", "skin", "appearance"),
        )
        for name in available_themes()
    ]


def build_default_registry(
    *,
    sessions: list[SessionItem] | None = None,
    models: list[ModelItem] | None = None,
    skills: list[RegistryItem] | None = None,
    plugins: list[RegistryItem] | None = None,
    recent_files: list[str | Path] | None = None,
) -> CommandCenterRegistry:
    registry = CommandCenterRegistry()
    registry.extend(local_command_actions())
    registry.extend(session_actions(list(sessions or [])))
    registry.extend(model_actions(list(models or [])))
    registry.extend(registry_item_actions(list(skills or []), kind="skill", category="Skills"))
    registry.extend(registry_item_actions(list(plugins or []), kind="plugin", category="Plugins"))
    registry.extend(recent_file_actions(list(recent_files or [])))
    registry.extend(document_vault_actions())
    registry.extend(runtime_actions())
    registry.extend(theme_actions())
    return registry


__all__ = [
    "CommandCenterRegistry",
    "build_default_registry",
    "document_vault_actions",
    "local_command_actions",
    "model_actions",
    "recent_file_actions",
    "registry_item_actions",
    "runtime_actions",
    "session_actions",
]
