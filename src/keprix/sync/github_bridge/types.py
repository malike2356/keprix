"""Types for the GitHub agent-sync durable memory bridge."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

GithubBridgeProduct = Literal["keprix", "hermes", "carina", "aiva", "shared"]
GithubBridgeScopeKind = Literal["workspace", "user", "shared"]


@dataclass
class GithubBridgeManifest:
    version: int = 1
    canonical_repo: str = "malike2356/agent-sync"
    default_branch: str = "main"
    read_folders: list[str] = field(
        default_factory=lambda: ["memory", "skills", "plans", "AGENTS.md", "DESIGN.md", "README.md", "sync"]
    )
    write_folders: list[str] = field(
        default_factory=lambda: [
            "memory/agents",
            "memory/sessions",
            "memory/projects",
            "memory/decisions.md",
            "plans",
            "sync/logs",
        ]
    )
    deny_globs: list[str] = field(
        default_factory=lambda: [
            ".env",
            ".env.*",
            "**/.env",
            "**/.env.*",
            "**/*secret*",
            "**/*credential*",
            "**/*password*",
            "**/*.pem",
            "**/*.key",
            "**/*token*",
            "**/node_modules/**",
            "**/.git/**",
        ]
    )
    products: dict[str, dict[str, Any]] = field(
        default_factory=lambda: {
            "shared": {"mount_folders": ["memory", "skills", "plans"], "agent_id": "shared"},
            "keprix": {
                "mount_folders": ["memory", "skills", "plans", "memory/projects/keprix.md"],
                "agent_id": "keprix",
            },
            "hermes": {
                "mount_folders": ["memory", "skills", "plans", "memory/projects/hermes.md"],
                "agent_id": "hermes",
            },
            "carina": {
                "mount_folders": ["memory", "skills", "plans", "memory/projects/carina.md"],
                "agent_id": "carina",
            },
            "aiva": {"mount_folders": ["memory", "skills", "plans", "memory/projects"], "agent_id": "aiva"},
        }
    )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class GithubBridgeConfig:
    scope_kind: GithubBridgeScopeKind = "workspace"
    scope_id: str | None = None
    enabled: bool = False
    owner: str = "malike2356"
    repo: str = "agent-sync"
    branch: str = "main"
    pull_interval_minutes: int = 15
    push_interval_minutes: int = 0
    allowed_folders: list[str] = field(default_factory=lambda: ["memory", "skills", "plans", "AGENTS.md"])
    human_edits_win: bool = True
    product: GithubBridgeProduct = "keprix"
    local_path: str | None = None
    last_pull_at: str | None = None
    last_push_at: str | None = None
    last_index_at: str | None = None
    last_error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


DEFAULT_MANIFEST = GithubBridgeManifest()
DEFAULT_CONFIG = GithubBridgeConfig()
