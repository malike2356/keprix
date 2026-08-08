"""Six-layer IsolationEnforcer for ABBIS sidecar requests."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


class IsolationDenied(PermissionError):
    def __init__(self, layer: str, reason: str) -> None:
        self.layer = layer
        self.reason = reason
        super().__init__(f"{layer}:{reason}")


@dataclass
class IsolationContext:
    product: str = "abbis"
    tenant_id: str = ""
    organisation_id: str = ""
    stakeholder: str = ""
    accessories: frozenset[str] = field(default_factory=frozenset)
    project_id: str = ""
    site_id: str = ""
    subject_id: str = ""
    purpose: str = ""
    grants: frozenset[str] = field(default_factory=frozenset)
    bdag_role: str = ""
    national_aggregate: bool = False
    onboarding_complete: bool = True


# Stakeholder -> default accessories (spec/27 seeds)
STAKEHOLDER_ACCESSORIES: dict[str, frozenset[str]] = {
    "S01": frozenset({"compliance.registry", "national.intelligence"}),
    "S07": frozenset(
        {
            "field.operations",
            "quotes.location",
            "drilling.projects",
            "compliance.registry",
            "calculators",
            "fleet.maintenance",
        }
    ),
    "S08": frozenset({"marketplace", "inventory.pos", "calculators"}),
    "S09": frozenset({"quotes.location", "marketplace", "contractor.crm", "calculators"}),
    "S14": frozenset({"association.ams", "workforce", "national.intelligence"}),
    "S15": frozenset({"field.operations"}),
    "S16": frozenset({"field.operations"}),
    "S17": frozenset({"field.operations"}),
    "S18": frozenset({"field.operations"}),
    "S19": frozenset({"client.portal", "calculators"}),
    "platform": frozenset({"core.auth", "core.brain"}),
}

ONBOARDING_ONLY_NODES = frozenset(
    {
        "get_onboarding_status",
        "complete_onboarding_step",
        "link_whatsapp",
        "link_telegram",
        "get_borehole_guidance",
    }
)

NATIONAL_NODES = frozenset(
    {
        "national_aggregate_summary",
        "association_digest",
        "bdag_intelligence_query",
    }
)

MIN_CELL_THRESHOLD = 5


class IsolationEnforcer:
    """Fail-closed isolation across product, tenant, stakeholder, accessory, project, subject."""

    def __init__(self, *, min_cell_threshold: int = MIN_CELL_THRESHOLD) -> None:
        self.min_cell_threshold = min_cell_threshold

    def assert_product(self, ctx: IsolationContext) -> None:
        if ctx.product != "abbis":
            raise IsolationDenied("L0_product", "wrong_product")

    def assert_tenant(self, ctx: IsolationContext, record_tenant: str | None = None) -> None:
        if not ctx.tenant_id:
            raise IsolationDenied("L1_tenant", "missing_tenant")
        if record_tenant and record_tenant != ctx.tenant_id and not ctx.national_aggregate:
            raise IsolationDenied("L1_tenant", "cross_tenant")

    def assert_accessory(self, ctx: IsolationContext, required: str | None) -> None:
        if not required:
            return
        allowed = ctx.accessories or STAKEHOLDER_ACCESSORIES.get(ctx.stakeholder, frozenset())
        if required not in allowed and "*" not in allowed:
            raise IsolationDenied("L2_accessory", f"missing:{required}")

    def assert_stakeholder_node(self, ctx: IsolationContext, node_key: str) -> None:
        if not ctx.onboarding_complete and node_key not in ONBOARDING_ONLY_NODES:
            raise IsolationDenied("L4_persona", "onboarding_incomplete")
        if node_key in NATIONAL_NODES:
            if ctx.stakeholder not in {"S01", "S14", "platform"} and not ctx.bdag_role:
                raise IsolationDenied("L4_persona", "national_not_entitled")
        if "node:*" in ctx.grants or "*" in ctx.grants:
            return
        need = f"node:{node_key}"
        if need not in ctx.grants and node_key not in ctx.grants:
            # Allow calculator family for entitled stakeholders with calculators accessory
            if node_key.endswith("_calculate") and "calculators" in (
                ctx.accessories or STAKEHOLDER_ACCESSORIES.get(ctx.stakeholder, frozenset())
            ):
                return
            raise IsolationDenied("L4_persona", f"grant_missing:{need}")

    def assert_project_scope(
        self,
        ctx: IsolationContext,
        *,
        record_project: str | None = None,
        record_site: str | None = None,
        record_subject: str | None = None,
    ) -> None:
        if ctx.project_id and record_project and record_project != ctx.project_id:
            raise IsolationDenied("L5_project", "cross_project")
        if ctx.site_id and record_site and record_site != ctx.site_id:
            raise IsolationDenied("L5_project", "cross_site")
        if ctx.subject_id and record_subject and record_subject != ctx.subject_id:
            raise IsolationDenied("L6_subject", "cross_subject")

    def assert_national_aggregate(self, ctx: IsolationContext, cell_count: int) -> None:
        if not ctx.national_aggregate and ctx.stakeholder not in {"S01", "S14"}:
            raise IsolationDenied("L_national", "aggregate_not_authorised")
        if cell_count < self.min_cell_threshold:
            raise IsolationDenied("L_national", "cell_threshold")

    def enforce(
        self,
        ctx: IsolationContext,
        *,
        node_key: str,
        required_accessory: str | None = None,
        record_tenant: str | None = None,
        record_project: str | None = None,
        record_site: str | None = None,
        record_subject: str | None = None,
        national_cell_count: int | None = None,
    ) -> dict[str, Any]:
        self.assert_product(ctx)
        self.assert_tenant(ctx, record_tenant)
        self.assert_accessory(ctx, required_accessory)
        self.assert_stakeholder_node(ctx, node_key)
        self.assert_project_scope(
            ctx,
            record_project=record_project,
            record_site=record_site,
            record_subject=record_subject,
        )
        if national_cell_count is not None:
            self.assert_national_aggregate(ctx, national_cell_count)
        return {
            "ok": True,
            "isolation_version": "abbis-spec-30@1.0.0",
            "layers": [
                "product",
                "organisation_tenant",
                "stakeholder",
                "accessory",
                "project_site",
                "subject",
            ],
            "tenant_id": ctx.tenant_id,
            "stakeholder": ctx.stakeholder,
            "node_key": node_key,
        }
