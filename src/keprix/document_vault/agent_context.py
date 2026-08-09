"""Trusted execution context for Document Vault agent tools (Prompt 650).

Workspace, actor, channel, and audience come from the session kwargs / env.
Model-supplied tenant IDs and host paths are never trusted.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Any

from keprix.document_vault.models import VaultError

_HOST_PATH = re.compile(r"^(/|~|[A-Za-z]:\\|\\\\)")
_PUBLIC_AUDIENCES = frozenset({"public", "external", "anonymous", "world"})


@dataclass(frozen=True)
class VaultAgentContext:
    workspace_id: str
    actor_id: str
    audience: str = "private"
    session_id: str = ""
    channel: str = "agent"
    grants: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "workspace_id": self.workspace_id,
            "actor_id": self.actor_id,
            "audience": self.audience,
            "session_id": self.session_id,
            "channel": self.channel,
            "grants": list(self.grants),
        }


def _first_str(*values: Any) -> str:
    for value in values:
        text = str(value or "").strip()
        if text:
            return text
    return ""


def reject_host_path(value: Any) -> None:
    text = str(value or "").strip()
    if not text:
        return
    if text.startswith("vault://"):
        return
    if _HOST_PATH.match(text) or ".." in text.split("/") or "\\" in text:
        raise VaultError("host_fs_forbidden", "Document Vault tools reject host filesystem paths")


def resolve_vault_context(args: dict[str, Any] | None = None, **kwargs: Any) -> VaultAgentContext:
    args = args or {}
    trusted_ws = _first_str(
        kwargs.get("trusted_workspace_id"),
        kwargs.get("workspace_id"),
        os.environ.get("KEPRIX_TRUSTED_WORKSPACE_ID"),
        os.environ.get("KEPRIX_WORKSPACE_ID"),
        kwargs.get("user_id"),
    )
    claimed_ws = _first_str(args.get("workspace_id"), args.get("tenant_id"))
    if claimed_ws and trusted_ws and claimed_ws != trusted_ws:
        raise VaultError("workspace_mismatch", "model-supplied workspace_id rejected")
    if claimed_ws and not trusted_ws:
        raise VaultError("workspace_mismatch", "workspace must come from trusted session context")
    workspace_id = trusted_ws or claimed_ws
    if not workspace_id:
        raise VaultError("workspace_mismatch", "no trusted workspace in session context")

    actor_id = _first_str(
        kwargs.get("actor_id"),
        kwargs.get("user_id"),
        args.get("actor_id"),
        "agent",
    )
    audience = _first_str(kwargs.get("audience"), args.get("audience"), "private").lower()
    if audience in _PUBLIC_AUDIENCES:
        raise VaultError("forbidden", "public audience cannot access the private Document Vault")

    # Reject any path-like args early.
    for key in ("path", "host_path", "file_path", "local_path", "cwd"):
        if key in args:
            reject_host_path(args.get(key))

    grants_raw = kwargs.get("grants") or args.get("grants") or ()
    if isinstance(grants_raw, str):
        grants = tuple(g.strip() for g in grants_raw.split(",") if g.strip())
    else:
        grants = tuple(str(g) for g in (grants_raw or ()))

    return VaultAgentContext(
        workspace_id=workspace_id,
        actor_id=actor_id,
        audience=audience or "private",
        session_id=_first_str(kwargs.get("session_id"), args.get("session_id")),
        channel=_first_str(kwargs.get("channel"), args.get("channel"), "agent"),
        grants=grants,
    )


__all__ = ["VaultAgentContext", "reject_host_path", "resolve_vault_context"]
