"""ElevenLabs-style permission catalog for Keprix API keys.

Deny-by-default: when a key is restricted, only explicitly granted
permissions are allowed. Internal /api/* paths map to scope groups so
API keys can reach workspace routes without becoming unscoped.
"""

from __future__ import annotations

from typing import Any, Literal

PermissionMode = Literal["none", "access", "read", "write"]

# Default new-key grants (chat-only OpenAI shape).
DEFAULT_ALLOWED_ENDPOINTS: list[str] = [
    "/v1/chat/completions",
    "/v1/models",
]
DEFAULT_ALLOWED_MODELS: list[str] = ["keprix"]

# Stable permission ids used in key.permissions and scopes.
SCOPE_CATALOG: list[dict[str, Any]] = [
    {
        "group": "OpenAI-compatible (/v1)",
        "items": [
            {
                "id": "v1.chat",
                "label": "Chat completions",
                "modes": ["none", "access"],
                "endpoints": ["/v1/chat/completions", "/v1/chat", "/v1/chat/stream"],
            },
            {
                "id": "v1.responses",
                "label": "Responses API",
                "modes": ["none", "access"],
                "endpoints": ["/v1/responses"],
            },
            {
                "id": "v1.embeddings",
                "label": "Embeddings",
                "modes": ["none", "access"],
                "endpoints": ["/v1/embeddings"],
            },
            {
                "id": "v1.models",
                "label": "Models",
                "modes": ["none", "access"],
                "endpoints": ["/v1/models"],
            },
            {
                "id": "v1.tools",
                "label": "Agent tool execution",
                "modes": ["none", "access"],
                "endpoints": ["/v1/tools"],
                "scope_flag": "tools:execute",
            },
        ],
    },
    {
        "group": "Workspace API (/api)",
        "items": [
            {
                "id": "api.conversations",
                "label": "Conversations / chat",
                "modes": ["none", "read", "write"],
                "path_prefixes": ["/api/conversations", "/api/conversation"],
            },
            {
                "id": "api.tasks",
                "label": "Tasks",
                "modes": ["none", "read", "write"],
                "path_prefixes": ["/api/workspace/tasks", "/v1/tasks"],
            },
            {
                "id": "api.audio",
                "label": "Voice / transcription",
                "modes": ["none", "access"],
                "path_prefixes": ["/api/audio"],
            },
            {
                "id": "api.memory",
                "label": "Memory / brain search",
                "modes": ["none", "read", "write"],
                "path_prefixes": ["/api/memory", "/api/brain", "/v1/memory"],
            },
            {
                "id": "api.files",
                "label": "Files / documents",
                "modes": ["none", "read", "write"],
                "path_prefixes": ["/api/files", "/api/documents", "/api/workspace/files"],
            },
            {
                "id": "api.tools",
                "label": "Tools admin",
                "modes": ["none", "read", "write"],
                "path_prefixes": ["/api/agent/tools", "/api/tools"],
            },
            {
                "id": "api.webhooks",
                "label": "Webhooks",
                "modes": ["none", "access"],
                "path_prefixes": ["/api/developer/webhooks"],
            },
            {
                "id": "api.usage",
                "label": "Usage / analytics (read)",
                "modes": ["none", "access"],
                "path_prefixes": ["/api/developer/usage", "/api/developer/logs"],
            },
        ],
    },
    {
        "group": "Administration",
        "items": [
            {
                "id": "api.admin",
                "label": "Admin API",
                "modes": ["none", "read", "write"],
                "path_prefixes": ["/api/admin"],
                "sensitive": True,
            },
            {
                "id": "api.developer.keys",
                "label": "Manage API keys",
                "modes": ["none", "access"],
                "path_prefixes": ["/api/developer/keys", "/api/developer/dashboard"],
                "sensitive": True,
            },
            {
                "id": "api.users",
                "label": "Workspace members",
                "modes": ["none", "read", "write"],
                "path_prefixes": ["/api/users", "/api/workspace/users"],
                "sensitive": True,
            },
        ],
    },
]


def default_permissions() -> dict[str, PermissionMode]:
    """Chat + models access only; everything else none."""
    perms: dict[str, PermissionMode] = {}
    for group in SCOPE_CATALOG:
        for item in group["items"]:
            perms[item["id"]] = "none"
    perms["v1.chat"] = "access"
    perms["v1.models"] = "access"
    return perms


def permissions_to_endpoints(permissions: dict[str, str]) -> list[str]:
    endpoints: list[str] = []
    for group in SCOPE_CATALOG:
        for item in group["items"]:
            mode = permissions.get(item["id"], "none")
            if mode in {"none", "", None}:
                continue
            for ep in item.get("endpoints") or []:
                if ep not in endpoints:
                    endpoints.append(ep)
    return endpoints


def permissions_to_scopes(permissions: dict[str, str]) -> dict[str, bool]:
    scopes: dict[str, bool] = {}
    for group in SCOPE_CATALOG:
        for item in group["items"]:
            mode = permissions.get(item["id"], "none")
            flag = item.get("scope_flag")
            if flag and mode not in {"none", "", None}:
                scopes[flag] = True
            # Also expose permission id as boolean for monitors / audits.
            if mode not in {"none", "", None}:
                scopes[item["id"]] = True
                scopes[f"{item['id']}:{mode}"] = True
    return scopes


def method_needs_write(method: str) -> bool:
    return method.upper() in {"POST", "PUT", "PATCH", "DELETE"}


def path_allowed_by_permissions(
    permissions: dict[str, str],
    *,
    path: str,
    method: str,
) -> bool:
    """Return True if restricted-key permissions allow this HTTP path/method."""
    normalized = path.split("?", 1)[0]
    needs_write = method_needs_write(method)

    for group in SCOPE_CATALOG:
        for item in group["items"]:
            mode = permissions.get(item["id"], "none")
            if mode in {"none", "", None}:
                continue

            endpoints = list(item.get("endpoints") or [])
            prefixes = list(item.get("path_prefixes") or [])

            matched = False
            if any(normalized == ep or normalized.startswith(ep + "/") for ep in endpoints):
                matched = True
            if any(normalized == p or normalized.startswith(p + "/") or normalized.startswith(p) for p in prefixes):
                matched = True
            if not matched:
                continue

            modes = item.get("modes") or ["none", "access"]
            if "access" in modes and mode == "access":
                return True
            if mode == "write":
                return True
            if mode == "read" and not needs_write:
                return True
            # Read grant cannot mutate.
            if mode == "read" and needs_write:
                return False
            return False
    return False


def catalog_for_api() -> dict[str, Any]:
    return {
        "groups": SCOPE_CATALOG,
        "defaults": {
            "restrict_key": True,
            "permissions": default_permissions(),
            "allowed_endpoints": list(DEFAULT_ALLOWED_ENDPOINTS),
            "allowed_models": list(DEFAULT_ALLOWED_MODELS),
            "auto_disable_if_leaked": True,
            "expire_after_days": None,
        },
    }
