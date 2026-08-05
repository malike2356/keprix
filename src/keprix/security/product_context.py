"""ProductContext: per-request product and workspace namespace binding."""

from __future__ import annotations

import contextvars
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ProductContext:
    """Immutable context for a single request.

    Set by IsolationMiddleware at request entry; read by the query filter
    and any code that needs to know what product/workspace it's operating in.
    """
    product_id: str                          # "aiva" | "abbis" | "petraclus" | "keprix"
    workspace_id: str
    tenant_id: str | None = None
    session_id: str | None = None
    scopes: frozenset[str] = field(default_factory=frozenset)

    def is_base_product(self) -> bool:
        return self.product_id == "keprix"

    def has_scope(self, scope: str) -> bool:
        return scope in self.scopes

    def to_dict(self) -> dict[str, Any]:
        return {
            "product_id": self.product_id,
            "workspace_id": self.workspace_id,
            "tenant_id": self.tenant_id,
            "session_id": self.session_id,
            "scopes": sorted(self.scopes),
        }


_PRODUCT_CONTEXT: contextvars.ContextVar[ProductContext | None] = (
    contextvars.ContextVar("product_context", default=None)
)


def get_product_context() -> ProductContext:
    """Return the current request's ProductContext.

    Raises RuntimeError if called outside a request (i.e., no middleware set it).
    """
    ctx = _PRODUCT_CONTEXT.get(None)
    if ctx is None:
        raise RuntimeError(
            "No product context set. Request is not going through IsolationMiddleware."
        )
    return ctx


def get_product_context_or_none() -> ProductContext | None:
    return _PRODUCT_CONTEXT.get(None)


def set_product_context(ctx: ProductContext) -> contextvars.Token:
    """Set the product context for the current task. Returns a reset token."""
    return _PRODUCT_CONTEXT.set(ctx)


def clear_product_context(token: contextvars.Token) -> None:
    """Reset the context variable to its pre-set state."""
    _PRODUCT_CONTEXT.reset(token)
