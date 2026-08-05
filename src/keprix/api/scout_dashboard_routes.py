"""Operator API for multi-product Scout dashboard data on Keprix."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from keprix.api.auth import require_admin

router = APIRouter(prefix="/api/v1/scout", tags=["scout-dashboard"])


class ProductPolicyUpdate(BaseModel):
    security_profile: str | None = None
    sandbox: dict[str, Any] = Field(default_factory=dict)
    egress: dict[str, Any] = Field(default_factory=dict)
    tools: dict[str, Any] = Field(default_factory=dict)
    governance: dict[str, Any] = Field(default_factory=dict)
    credentials: dict[str, Any] = Field(default_factory=dict)
    audit: dict[str, Any] = Field(default_factory=dict)


class ProductAlertsUpdate(BaseModel):
    alert_channels: list[dict[str, Any]] = Field(default_factory=list)
    quiet_hours: dict[str, int] = Field(default_factory=lambda: {"start": 22, "end": 7})
    custom_rules: list[dict[str, Any]] = Field(default_factory=list)


@router.get("/dashboard/summary")
async def scout_dashboard_summary(_admin: str = Depends(require_admin)) -> dict[str, Any]:
    from keprix.security.scout_correlation import dashboard_summary

    return dashboard_summary()


@router.get("/agents")
async def scout_list_agents(_admin: str = Depends(require_admin)) -> dict[str, Any]:
    from keprix.security.scout_metrics import product_metrics
    from keprix.security.scout_registration import ScoutRegistration

    agents = ScoutRegistration().list_local_registrations()
    metrics = product_metrics()
    rows = []
    for agent in agents:
        pid = str(agent.get("product_id") or "")
        m = metrics.get(pid, {})
        rows.append(
            {
                **agent,
                "signals_24h": int(m.get("signals_24h") or 0),
                "alerts_warning": int(m.get("alerts_warning") or 0),
                "alerts_critical": int(m.get("alerts_critical") or 0),
            }
        )
    return {"agents": rows, "count": len(rows)}


@router.get("/policies")
async def scout_list_policies(_admin: str = Depends(require_admin)) -> dict[str, Any]:
    from keprix.security.product_policy import list_policies

    policies = list_policies()
    return {"policies": policies, "count": len(policies)}


@router.get("/policies/{product_id}")
async def scout_get_policy(product_id: str, _admin: str = Depends(require_admin)) -> dict[str, Any]:
    from keprix.security.operator_policy import get_operator_policy
    from keprix.security.product_policy import get_policy

    policy = get_policy(product_id)
    if policy is None:
        raise HTTPException(status_code=404, detail=f"policy not found for product '{product_id}'")
    operator = get_operator_policy(product_id=product_id)
    return {
        "product_id": product_id,
        "policy": policy,
        "operator_policy": operator.to_dict(),
    }


@router.put("/policies/{product_id}")
async def scout_update_policy(
    product_id: str,
    body: ProductPolicyUpdate,
    _admin: str = Depends(require_admin),
) -> dict[str, Any]:
    from keprix.security.product_policy import apply_product_policy

    policy = body.model_dump(exclude_none=True)
    record = apply_product_policy(product_id, policy, updated_by="operator_api")
    return {"product_id": product_id, "policy": record}


@router.get("/policies/{product_id}/history")
async def scout_policy_history(
    product_id: str,
    _admin: str = Depends(require_admin),
) -> dict[str, Any]:
    from keprix.security.product_policy import policy_history

    return {"product_id": product_id, "history": policy_history(product_id)}


@router.get("/correlation")
async def scout_correlation(_admin: str = Depends(require_admin)) -> dict[str, Any]:
    from keprix.security.scout_correlation import correlate_attacks

    attacks = correlate_attacks()
    return {"correlated_attacks": attacks, "count": len(attacks)}


@router.get("/dashboard/alerts")
async def scout_dashboard_alerts(_admin: str = Depends(require_admin)) -> dict[str, Any]:
    from keprix.security.scout_alerts import ScoutAlertConfig
    from keprix.security.scout_metrics import product_metrics

    alerts = ScoutAlertConfig().list_all()
    metrics = product_metrics()
    active: list[dict[str, Any]] = []
    for product_id, row in metrics.items():
        warning = int(row.get("alerts_warning") or 0)
        critical = int(row.get("alerts_critical") or 0)
        if warning or critical:
            active.append(
                {
                    "product_id": product_id,
                    "alerts_warning": warning,
                    "alerts_critical": critical,
                    "config": alerts.get(product_id) or {},
                }
            )
    return {"active_alerts": active, "configurations": alerts, "count": len(active)}


@router.put("/dashboard/alerts/{product_id}")
async def scout_configure_alerts(
    product_id: str,
    body: ProductAlertsUpdate,
    _admin: str = Depends(require_admin),
) -> dict[str, Any]:
    from keprix.security.scout_alerts import ScoutAlertConfig

    record = ScoutAlertConfig().configure_product_alerts(product_id, body.model_dump())
    return {"product_id": product_id, "alerts": record}
