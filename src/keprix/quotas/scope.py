"""Actor-scoped quota keys (workspace, agent, API token, user, product).

Never trust scope IDs from request body for enforcement. Callers must pass
IDs already resolved from auth, session, or server-side product context.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

ScopeType = Literal["workspace", "agent", "api_token", "user", "product"]


@dataclass(frozen=True)
class QuotaScope:
    scope_type: ScopeType
    scope_id: str

    def key(self) -> str:
        return f"{self.scope_type}:{self.scope_id}"

    def to_dict(self) -> dict[str, str]:
        return {"scope_type": self.scope_type, "scope_id": self.scope_id}


def make_scope(scope_type: ScopeType, scope_id: str | None, *, fallback: str = "default") -> QuotaScope:
    sid = (scope_id or "").strip() or fallback
    return QuotaScope(scope_type=scope_type, scope_id=sid)


def scopes_for_request(
    *,
    workspace_id: str | None = None,
    user_id: str | None = None,
    agent_id: str | None = None,
    api_token_id: str | None = None,
    product_id: str | None = None,
) -> list[QuotaScope]:
    """Build the ordered list of scopes to enforce for one action.

    More specific scopes (token, agent) are checked first; product last.
    """
    scopes: list[QuotaScope] = []
    if api_token_id:
        scopes.append(make_scope("api_token", api_token_id))
    if agent_id:
        scopes.append(make_scope("agent", agent_id))
    if user_id:
        scopes.append(make_scope("user", user_id))
    if workspace_id:
        scopes.append(make_scope("workspace", workspace_id))
    if product_id:
        scopes.append(make_scope("product", product_id))
    elif not scopes:
        scopes.append(make_scope("product", "keprix"))
    return scopes


def estimate_tokens_from_payload(payload: Any) -> int:
    """Cheap ~4 chars/token estimate for quota budgeting."""
    if payload is None:
        return 0
    if isinstance(payload, (int, float)):
        return max(0, int(payload))
    if isinstance(payload, str):
        text = payload
    else:
        try:
            import json

            text = json.dumps(payload, default=str)
        except Exception:
            text = str(payload)
    return max(0, (len(text) + 3) // 4)
