"""Property vertical discovery adapters (CSV on; portals experimental/off)."""

from __future__ import annotations

import os
from typing import Any

from keprix.discovery.adapters.csv_import import CsvDiscoveryAdapter
from keprix.discovery.models import (
    AdapterHealth,
    AdapterHealthStatus,
    AdapterManifest,
    DiscoverLimits,
    DiscoverQuery,
    LeadCandidate,
)

PROPERTY_PORTAL_FLAG = "KEPRIX_PROPERTY_PORTAL_ADAPTERS"
LEGAL_CHECKLIST = "docs/security/property-portal-legal-checklist.md"


def property_portals_enabled(workspace_id: str | None = None) -> bool:
    if workspace_id:
        try:
            from keprix.crm.connections import workspace_flag_enabled
            from keprix.crm.store import get_crm_store

            if workspace_flag_enabled(get_crm_store(), workspace_id, "property_portal_adapters_enabled"):
                return True
        except Exception:
            pass
    raw = os.environ.get(PROPERTY_PORTAL_FLAG, "0").strip().lower()
    return raw in {"1", "true", "yes", "on"}


class PropertyCsvAdapter(CsvDiscoveryAdapter):
    name = "property_csv"
    domain_packs = ["property"]

    @property
    def manifest(self) -> AdapterManifest:
        base = super().manifest
        return AdapterManifest(
            name=self.name,
            title="Property CSV import",
            description="Always-on property sheet / CSV discovery (no portal scrape).",
            licence_ref=base.licence_ref,
            source_licence=base.source_licence,
            permitted_purpose="property_pipeline_review",
            allowed_fields=list(base.allowed_fields),
            retention=base.retention,
            jurisdiction=base.jurisdiction,
            contact_use_eligible=False,
            outreach_allowed=False,
            rate_limit_per_minute=60,
            domain_packs=["property"],
            docs_path="docs/features/property-vertical-pack.md",
        )

    def discover(self, query: DiscoverQuery, limits: DiscoverLimits) -> list[LeadCandidate]:
        q = DiscoverQuery(
            text=query.text,
            params=query.params,
            domain_pack=query.domain_pack or "property",
            workspace_id=query.workspace_id,
        )
        candidates = super().discover(q, limits)
        for cand in candidates:
            cand.source = self.name
            cand.domain_pack = "property"
        return candidates


class _PortalStub:
    name = "property_portal"
    domain_packs = ["property"]
    title = "Property portal HTTP (experimental)"
    portal = "portal"

    @property
    def manifest(self) -> AdapterManifest:
        return AdapterManifest(
            name=self.name,
            title=self.title,
            description=(
                f"Experimental {self.portal} HTTP adapter. Default OFF. "
                f"Requires {PROPERTY_PORTAL_FLAG}=1, Soft Wall, and legal checklist acknowledgement. "
                "Prefer licensed/API data. HTML scrape carries ToS risk."
            ),
            licence_ref=LEGAL_CHECKLIST,
            source_licence=f"{self.portal} Terms of Use; scrape often prohibited",
            permitted_purpose="experimental_listing_review",
            contact_use_eligible=False,
            outreach_allowed=False,
            rate_limit_per_minute=5,
            domain_packs=["property"],
            feature_flag=PROPERTY_PORTAL_FLAG,
            experimental=True,
            docs_path=LEGAL_CHECKLIST,
        )

    def health(self) -> AdapterHealth:
        if not property_portals_enabled():
            return AdapterHealth(
                name=self.name,
                status=AdapterHealthStatus.DISABLED,
                message=(
                    f"{self.portal} adapter disabled. Set {PROPERTY_PORTAL_FLAG}=1 and complete "
                    f"{LEGAL_CHECKLIST}. Keprix does not claim to scrape {self.portal} unless "
                    "the flag is on and the checklist is acknowledged."
                ),
                configured=False,
                enabled=False,
                details={"flag": PROPERTY_PORTAL_FLAG, "checklist": LEGAL_CHECKLIST},
            )
        return AdapterHealth(
            name=self.name,
            status=AdapterHealthStatus.NOT_CONFIGURED,
            message=(
                f"{self.portal} experimental path enabled by flag, but no licensed API credentials "
                "are configured. HTML scrape remains blocked without Soft Wall + checklist ack."
            ),
            configured=False,
            enabled=True,
            details={"flag": PROPERTY_PORTAL_FLAG, "checklist": LEGAL_CHECKLIST},
        )

    def cost_forecast(self, query: DiscoverQuery, limits: DiscoverLimits) -> dict[str, Any]:
        return {"units": 0.0, "currency": "blocked", "note": "portal adapters refuse until licensed"}

    def discover(self, query: DiscoverQuery, limits: DiscoverLimits) -> list[LeadCandidate]:
        from keprix.crm.property_portal_gate import assert_portal_job_allowed, kill_switch_engaged

        if kill_switch_engaged():
            raise RuntimeError(f"{self.portal} kill switch engaged; job stopped safely.")
        if not property_portals_enabled():
            raise RuntimeError(
                f"{self.portal} adapter is disabled. Set {PROPERTY_PORTAL_FLAG}=1 and review "
                f"{LEGAL_CHECKLIST}. Prefer CSV/Companies House/web_directory."
            )
        # Prefer workspace checklist ack recorded via Soft Wall UI; query param still accepted.
        ws = query.workspace_id
        if ws:
            try:
                from keprix.crm.store import get_crm_store

                gate = assert_portal_job_allowed(get_crm_store(), ws)
                if not gate.get("ok") and not bool(query.params.get("legal_checklist_acknowledged")):
                    raise RuntimeError(
                        f"{self.portal} requires checklist acknowledgment ({LEGAL_CHECKLIST}). "
                        f"error={gate.get('error')}"
                    )
            except RuntimeError:
                raise
            except Exception:
                ack = bool(query.params.get("legal_checklist_acknowledged"))
                if not ack:
                    raise RuntimeError(
                        f"{self.portal} requires Soft Wall approval and legal_checklist_acknowledged=true "
                        f"({LEGAL_CHECKLIST}). Prefer licensed/API feeds over HTML scrape."
                    )
        else:
            ack = bool(query.params.get("legal_checklist_acknowledged"))
            if not ack:
                raise RuntimeError(
                    f"{self.portal} requires Soft Wall approval and legal_checklist_acknowledged=true "
                    f"({LEGAL_CHECKLIST}). Prefer licensed/API feeds over HTML scrape."
                )
        # Licensed feed path when credentials present.
        feed_key = os.environ.get("KEPRIX_PROPERTY_FEED_URL", "").strip()
        if feed_key and query.params.get("feed_rows"):
            rows = query.params.get("feed_rows") or []
            out: list[LeadCandidate] = []
            for idx, item in enumerate(rows):
                if not isinstance(item, dict):
                    continue
                out.append(
                    LeadCandidate(
                        company=str(item.get("agent") or item.get("company") or f"{self.portal} listing {idx}"),
                        contacts=[],
                        urls=[str(item.get("url"))] if item.get("url") else [],
                        geo={"postcode": item.get("postcode")},
                        source=self.name,
                        external_id=str(item.get("id") or f"{self.name}-{idx}"),
                        raw=dict(item),
                        score_hint=0.5,
                        domain_pack="property",
                    )
                )
                if len(out) >= limits.max_results:
                    break
            return out
        # Even with flag+ack, do not ship a scrape implementation here.
        raise RuntimeError(
            f"{self.portal} licensed API credentials are not configured. "
            "Keprix refuses HTML scrape by default."
        )


class RightmoveHttpAdapter(_PortalStub):
    name = "rightmove_http"
    title = "Rightmove HTTP (experimental, default off)"
    portal = "Rightmove"


class ZooplaHttpAdapter(_PortalStub):
    name = "zoopla_http"
    title = "Zoopla HTTP (experimental, default off)"
    portal = "Zoopla"
