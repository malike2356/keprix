"""Network egress audit API routes.

Endpoints:
  GET /api/admin/network-egress         - tail recent egress decisions
  GET /api/admin/network-egress/policy  - show registered product egress policies
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from keprix.auth.dependencies import require_admin
from keprix.security.egress_audit import get_egress_audit
from keprix.security.egress_policy import get_egress_policy

router = APIRouter(prefix="/api/admin/network-egress", tags=["admin", "security"])


@router.get("")
async def list_egress_events(
    n: int = Query(default=50, ge=1, le=500),
    product_id: str | None = Query(default=None),
    decision: str | None = Query(default=None, pattern="^(ALLOWED|BLOCKED)$"),
    _admin: dict = Depends(require_admin),
) -> dict:
    """Return recent egress audit entries, optionally filtered by product and decision."""
    _ = _admin
    audit = get_egress_audit()
    fetch_n = n if not product_id and not decision else min(n * 10, 500)
    entries = audit.tail(n=fetch_n)

    if product_id:
        entries = [e for e in entries if e.get("product_id") == product_id]
    if decision:
        entries = [e for e in entries if e.get("decision") == decision]

    entries = entries[-n:]
    return {"count": len(entries), "entries": entries}


@router.get("/policy")
async def list_egress_policies(_admin: dict = Depends(require_admin)) -> dict:
    """Return the registered egress policy for all products."""
    _ = _admin
    policy = get_egress_policy()
    return {
        "products": policy.list_products(),
        "policies": policy.snapshot(),
    }
