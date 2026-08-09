"""Product pack readiness aggregation (prompt 643)."""

from __future__ import annotations

from keprix.product_sidecar.readiness import build_product_readiness


def test_build_product_readiness_propreneur() -> None:
    ready = build_product_readiness("propreneur")
    assert ready["engine_connectivity"] in {"ok", "disabled"}
    counts = ready["operation_counts"]
    assert counts["executable"] == counts["live"] + counts["approval_required"]
    assert ready["pack_readiness"]["capability_honesty"] in {
        "ok",
        "partial_fail_closed",
        "fail_closed_remediation",
    }
    assert "TrustedExecutionContext" in ready["actor_and_tenant_binding"]["model"]
    assert ready["emergency_controls"]["admin_route"].endswith("/admin/kill")
