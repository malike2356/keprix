"""Declarative resource kinds for Keprix tools and connectors.

Reimplements the resource-scope pattern (not AGPL source). Each service lists
restrictable kinds and how to extract IDs from tool arguments.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

MatchMode = Literal["exact", "prefix"]
ActionClass = Literal["read", "write", "delete", "deploy", "mutate", "side_effect"]


@dataclass(frozen=True)
class ResourceKindSpec:
    kind: str
    label: str
    match_mode: MatchMode = "exact"
    # Arg keys that carry the resource id (string or list).
    arg_fields: tuple[str, ...] = ()
    # Nested dotted paths into args (arrays fan out).
    nested_fields: tuple[str, ...] = ()
    # Regex patterns run against stringified args / path-like fields; group 1 = id.
    arg_patterns: tuple[str, ...] = ()
    # True when the call clearly targets this kind even if no id was found.
    targets_kind_hints: tuple[str, ...] = ()


@dataclass(frozen=True)
class ServiceResourceSpec:
    service: str
    label: str
    kinds: tuple[ResourceKindSpec, ...] = ()
    # Map tool name prefixes / exact names to this service.
    tool_prefixes: tuple[str, ...] = ()
    tool_names: tuple[str, ...] = ()
    # Default action class by tool name substring heuristics (overridable).
    write_hints: tuple[str, ...] = (
        "write",
        "create",
        "update",
        "delete",
        "remove",
        "send",
        "post",
        "put",
        "patch",
        "deploy",
        "mutate",
        "edit",
        "upload",
        "execute",
        "run",
        "apply",
    )


# Keprix-oriented registry (tools + common connectors). Empty allow-lists mean unrestricted.
SERVICE_RESOURCE_REGISTRY: dict[str, ServiceResourceSpec] = {
    "github": ServiceResourceSpec(
        service="github",
        label="GitHub",
        tool_prefixes=("github", "gh_"),
        tool_names=("git_clone", "git_push", "create_pull_request"),
        kinds=(
            ResourceKindSpec(
                kind="repos",
                label="Repositories",
                arg_fields=("repo", "repository", "full_name", "repo_full_name"),
                nested_fields=("repository.full_name", "repository.name"),
                arg_patterns=(r"(?:github\.com[:/])([\w.-]+/[\w.-]+)",),
                targets_kind_hints=("repo", "repository", "pull_request", "commit"),
            ),
        ),
    ),
    "filesystem": ServiceResourceSpec(
        service="filesystem",
        label="Local filesystem",
        tool_prefixes=("file", "fs_", "path"),
        tool_names=("read_file", "write_file", "list_dir", "search_files", "edit_file", "delete_file"),
        kinds=(
            ResourceKindSpec(
                kind="paths",
                label="Paths",
                match_mode="prefix",
                arg_fields=("path", "file_path", "filepath", "directory", "dir", "target"),
                nested_fields=("file.path",),
                targets_kind_hints=("path", "file", "directory"),
            ),
        ),
    ),
    "mcp": ServiceResourceSpec(
        service="mcp",
        label="MCP servers",
        tool_prefixes=("mcp_", "mcp:"),
        tool_names=("mcp_call", "mcp_tool"),
        kinds=(
            ResourceKindSpec(
                kind="servers",
                label="Servers",
                arg_fields=("server", "server_name", "mcp_server", "server_id"),
                targets_kind_hints=("server", "mcp"),
            ),
        ),
    ),
    "slack": ServiceResourceSpec(
        service="slack",
        label="Slack",
        tool_prefixes=("slack",),
        kinds=(
            ResourceKindSpec(
                kind="channels",
                label="Channels",
                arg_fields=("channel", "channel_id", "channel_name"),
                arg_patterns=(r"#[\w-]+", r"C[A-Z0-9]{8,}"),
                targets_kind_hints=("channel", "slack"),
            ),
        ),
    ),
    "notion": ServiceResourceSpec(
        service="notion",
        label="Notion",
        tool_prefixes=("notion",),
        kinds=(
            ResourceKindSpec(
                kind="pages",
                label="Pages",
                arg_fields=("page_id", "page", "block_id"),
                targets_kind_hints=("page", "notion"),
            ),
        ),
    ),
    "gdrive": ServiceResourceSpec(
        service="gdrive",
        label="Google Drive",
        tool_prefixes=("gdrive", "google_drive", "drive_"),
        kinds=(
            ResourceKindSpec(
                kind="folders",
                label="Folders",
                match_mode="prefix",
                arg_fields=("folder_id", "folder", "parent_id", "drive_id"),
                targets_kind_hints=("folder", "drive"),
            ),
        ),
    ),
    "calendar": ServiceResourceSpec(
        service="calendar",
        label="Calendar",
        tool_prefixes=("calendar", "gcal"),
        kinds=(
            ResourceKindSpec(
                kind="calendars",
                label="Calendars",
                arg_fields=("calendar_id", "calendar", "cal_id"),
                targets_kind_hints=("calendar", "event"),
            ),
        ),
    ),
    "database": ServiceResourceSpec(
        service="database",
        label="Database",
        tool_prefixes=("db_", "sql_", "postgres", "mysql"),
        tool_names=("execute_sql", "query_database"),
        kinds=(
            ResourceKindSpec(
                kind="tables",
                label="Tables",
                arg_fields=("table", "table_name", "relation"),
                targets_kind_hints=("table", "schema", "sql"),
            ),
        ),
    ),
    "deploy": ServiceResourceSpec(
        service="deploy",
        label="Deployments",
        tool_prefixes=("deploy", "kubectl", "helm"),
        tool_names=("deploy_app", "rollout", "kubectl_apply"),
        kinds=(
            ResourceKindSpec(
                kind="targets",
                label="Deploy targets",
                arg_fields=("target", "environment", "cluster", "namespace", "app"),
                targets_kind_hints=("deploy", "rollout", "release"),
            ),
        ),
        write_hints=("deploy", "apply", "rollout", "release", "scale"),
    ),
    "mutation": ServiceResourceSpec(
        service="mutation",
        label="Self-coding / mutation",
        tool_prefixes=("mutation", "self_coding", "code_"),
        tool_names=("synthesize_tool", "run_mutation", "edit_repo"),
        kinds=(
            ResourceKindSpec(
                kind="workspaces",
                label="Coding workspaces",
                match_mode="prefix",
                arg_fields=("workspace", "workspace_id", "repo_path", "target_dir"),
                targets_kind_hints=("mutation", "repo", "workspace"),
            ),
        ),
        write_hints=("mutate", "edit", "write", "synthesize", "apply"),
    ),
    "hosted_app": ServiceResourceSpec(
        service="hosted_app",
        label="Hosted apps",
        tool_prefixes=("agent_app", "hosted_app"),
        kinds=(
            ResourceKindSpec(
                kind="apps",
                label="Apps",
                arg_fields=("app_id", "app", "application_id"),
                targets_kind_hints=("app", "application"),
            ),
        ),
    ),
}


def list_services() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for spec in SERVICE_RESOURCE_REGISTRY.values():
        out.append(
            {
                "service": spec.service,
                "label": spec.label,
                "kinds": [
                    {
                        "kind": k.kind,
                        "label": k.label,
                        "match_mode": k.match_mode,
                    }
                    for k in spec.kinds
                ],
            }
        )
    return sorted(out, key=lambda row: row["service"])


def resolve_service_for_tool(tool_name: str) -> ServiceResourceSpec | None:
    name = (tool_name or "").strip().lower()
    if not name:
        return None
    for spec in SERVICE_RESOURCE_REGISTRY.values():
        if name in {t.lower() for t in spec.tool_names}:
            return spec
        for prefix in spec.tool_prefixes:
            p = prefix.lower()
            if name.startswith(p) or name.startswith(p.rstrip("_") + "_") or name.startswith(p.rstrip(":") + ":"):
                return spec
    return None
