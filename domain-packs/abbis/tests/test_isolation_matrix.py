"""Six-layer isolation and national aggregate fail-closed tests."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

PACK_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACK_ROOT))

from isolation import IsolationContext, IsolationDenied, IsolationEnforcer  # noqa: E402
from tools.handlers import national_aggregate_summary_handler  # noqa: E402
import json


def test_cross_tenant_denied() -> None:
    enforcer = IsolationEnforcer()
    ctx = IsolationContext(
        product="abbis",
        tenant_id="tenant-alpha",
        stakeholder="S07",
        accessories=frozenset({"field.operations"}),
        grants=frozenset({"node:job_brief"}),
    )
    with pytest.raises(IsolationDenied) as exc:
        enforcer.enforce(ctx, node_key="job_brief", record_tenant="tenant-beta")
    assert exc.value.layer == "L1_tenant"


def test_accessory_denied() -> None:
    enforcer = IsolationEnforcer()
    ctx = IsolationContext(
        product="abbis",
        tenant_id="tenant-alpha",
        stakeholder="S19",
        accessories=frozenset({"client.portal"}),
        grants=frozenset({"*"}),
    )
    with pytest.raises(IsolationDenied):
        enforcer.enforce(ctx, node_key="stock_usage_propose", required_accessory="inventory.pos")


def test_national_cell_threshold() -> None:
    enforcer = IsolationEnforcer()
    ctx = IsolationContext(
        product="abbis",
        tenant_id="bdag",
        stakeholder="S14",
        accessories=frozenset({"national.intelligence"}),
        grants=frozenset({"*"}),
        national_aggregate=True,
        bdag_role="exec",
    )
    with pytest.raises(IsolationDenied) as exc:
        enforcer.enforce(ctx, node_key="national_aggregate_summary", national_cell_count=2)
    assert "cell_threshold" in exc.value.reason


def test_national_handler_rejects_small_cell() -> None:
    raw = national_aggregate_summary_handler(
        {
            "national_cell_count": 2,
            "stakeholder": "S14",
            "tenant_id": "bdag",
            "accessories": ["national.intelligence"],
            "grants": ["*"],
        }
    )
    data = json.loads(raw)
    assert data.get("status") == "error"


def test_onboarding_blocks_writes() -> None:
    enforcer = IsolationEnforcer()
    ctx = IsolationContext(
        product="abbis",
        tenant_id="tenant-alpha",
        stakeholder="S07",
        accessories=frozenset({"field.operations"}),
        grants=frozenset({"*"}),
        onboarding_complete=False,
    )
    with pytest.raises(IsolationDenied):
        enforcer.enforce(ctx, node_key="drilling_log_assist")
