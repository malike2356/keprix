"""Trusted execution context for product callbacks (prompt 638).

Server-side only. Never expose these fields in model-visible tool schemas.
The language model cannot choose or override identity claims.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


IDENTITY_BODY_KEYS = frozenset(
    {
        "workspace_id",
        "user_id",
        "worker_id",
        "conversation_id",
        "platform_user_id",
        "platform_conversation_id",
        "platform_scope",
        "correlation_id",
        "idempotency_key",
        "approval_token",
        "approval_id",
        "actor_scopes",
        "actor_id",
        "actor_type",
        "granted_scopes",
        "channel_binding",
        "approval_evidence",
        "product",
        "tenant_id",
        "etag",
        "if_match",
        "authorization_bearer",
        "product_host",
        "api_key",
        "auth_header",
        "authorization",
    }
)

TRUSTED_HEADER_WORKSPACE = "X-Keprix-Trusted-Workspace-Id"
TRUSTED_HEADER_ACTOR = "X-Keprix-Trusted-Actor-Id"
TRUSTED_HEADER_ACTOR_TYPE = "X-Keprix-Trusted-Actor-Type"
TRUSTED_HEADER_CONVERSATION = "X-Keprix-Trusted-Conversation-Id"
TRUSTED_HEADER_PRODUCT = "X-Keprix-Trusted-Product"
TRUSTED_HEADER_CORRELATION = "X-Correlation-Id"
TRUSTED_HEADER_CHANNEL = "X-Keprix-Trusted-Channel"


@dataclass(frozen=True)
class TrustedExecutionContext:
    """Identity and control plane fields injected by Keprix, not the model."""

    product: str
    workspace_id: str
    actor_id: str
    actor_type: str = "tenant_user"  # tenant_user | platform_user | worker
    conversation_id: str = ""
    worker_id: str = ""
    correlation_id: str = ""
    granted_scopes: tuple[str, ...] = ()
    channel_binding: str = ""
    approval_evidence: str = ""
    idempotency_key: str = ""
    if_match: str = ""
    platform_user_id: str = ""
    platform_conversation_id: str = ""
    platform_scope: bool = False
    # Server-side only product credentials / Host for tenancy (never from model args).
    authorization_bearer: str = ""
    product_host: str = ""

    def to_callback_fields(self) -> dict[str, Any]:
        """Top-level JSON fields Propreneur's fail-closed controller expects."""
        out: dict[str, Any] = {
            "workspace_id": self.workspace_id,
            "correlation_id": self.correlation_id,
            "actor_type": self.actor_type,
            "product": self.product,
        }
        if self.actor_type == "platform_user" or self.platform_scope:
            out["platform_scope"] = True
            out["platform_user_id"] = self.platform_user_id or self.actor_id
            if self.platform_conversation_id or self.conversation_id:
                out["platform_conversation_id"] = (
                    self.platform_conversation_id or self.conversation_id
                )
        else:
            out["user_id"] = self.actor_id
            if self.conversation_id:
                out["conversation_id"] = self.conversation_id
            if self.worker_id:
                out["worker_id"] = self.worker_id
        if self.idempotency_key:
            out["idempotency_key"] = self.idempotency_key
        if self.approval_evidence:
            out["approval_token"] = self.approval_evidence
        if self.granted_scopes:
            out["actor_scopes"] = list(self.granted_scopes)
        if self.channel_binding:
            out["channel_binding"] = self.channel_binding
        if self.if_match:
            out["etag"] = self.if_match
        return out

    def to_headers(self) -> dict[str, str]:
        headers = {
            TRUSTED_HEADER_PRODUCT: self.product,
            TRUSTED_HEADER_WORKSPACE: self.workspace_id,
            TRUSTED_HEADER_ACTOR: self.actor_id,
            TRUSTED_HEADER_ACTOR_TYPE: self.actor_type,
        }
        if self.conversation_id:
            headers[TRUSTED_HEADER_CONVERSATION] = self.conversation_id
        if self.correlation_id:
            headers[TRUSTED_HEADER_CORRELATION] = self.correlation_id
        if self.channel_binding:
            headers[TRUSTED_HEADER_CHANNEL] = self.channel_binding
        if self.idempotency_key:
            headers["Idempotency-Key"] = self.idempotency_key
        if self.if_match:
            headers["If-Match"] = self.if_match
        token = (self.authorization_bearer or "").strip()
        if token:
            headers["Authorization"] = token if token.lower().startswith("bearer ") else f"Bearer {token}"
        if self.product_host:
            headers["Host"] = self.product_host.strip()
        return headers

    def as_public_dict(self) -> dict[str, Any]:
        """Safe debug view (no secrets)."""
        return asdict(self)


def strip_identity_from_model_args(arguments: dict[str, Any] | None) -> dict[str, Any]:
    """Remove identity/control keys the model must not override."""
    raw = dict(arguments or {})
    return {k: v for k, v in raw.items() if k not in IDENTITY_BODY_KEYS}


def merge_trusted_callback_body(
    model_arguments: dict[str, Any] | None,
    trusted: TrustedExecutionContext,
) -> dict[str, Any]:
    """Model args (sanitized) + server-injected trusted fields (trusted wins)."""
    body = strip_identity_from_model_args(model_arguments)
    body.update(trusted.to_callback_fields())
    return body


def trusted_context_from_carina_tool(
    tool_def: dict[str, Any],
    *,
    fallback_workspace_id: str,
    fallback_product: str = "propreneur",
    fallback_correlation_id: str = "",
) -> TrustedExecutionContext:
    """Build trusted context from Propreneur-emitted carina_tools metadata."""
    workspace = str(
        tool_def.get("workspace_id") or tool_def.get("tenant_id") or fallback_workspace_id or ""
    ).strip()
    platform_user = str(tool_def.get("platform_user_id") or "").strip()
    user_id = str(tool_def.get("user_id") or "").strip()
    worker_id = str(tool_def.get("worker_id") or "").strip()
    platform_scope = bool(tool_def.get("platform_scope")) or bool(platform_user)
    if platform_scope:
        actor_id = platform_user or user_id
        actor_type = "platform_user"
    elif worker_id and not user_id:
        actor_id = worker_id
        actor_type = "worker"
    else:
        actor_id = user_id or worker_id
        actor_type = "tenant_user"
    scopes_raw = tool_def.get("granted_scopes") or tool_def.get("actor_scopes") or []
    if isinstance(scopes_raw, str):
        scopes = tuple(s.strip() for s in scopes_raw.split(",") if s.strip())
    elif isinstance(scopes_raw, (list, tuple)):
        scopes = tuple(str(s) for s in scopes_raw)
    else:
        scopes = ()
    return TrustedExecutionContext(
        product=str(tool_def.get("product") or fallback_product).strip() or fallback_product,
        workspace_id=workspace,
        actor_id=actor_id,
        actor_type=actor_type,
        conversation_id=str(
            tool_def.get("conversation_id") or tool_def.get("platform_conversation_id") or ""
        ).strip(),
        worker_id=worker_id,
        correlation_id=str(
            tool_def.get("correlation_id") or fallback_correlation_id or ""
        ).strip(),
        granted_scopes=scopes,
        channel_binding=str(tool_def.get("channel_binding") or tool_def.get("channel") or "").strip(),
        approval_evidence=str(
            tool_def.get("approval_evidence") or tool_def.get("approval_token") or ""
        ).strip(),
        idempotency_key=str(tool_def.get("idempotency_key") or "").strip(),
        platform_user_id=platform_user,
        platform_conversation_id=str(tool_def.get("platform_conversation_id") or "").strip(),
        platform_scope=platform_scope,
    )
