"""Social discovery adapters: API-first stubs (scrapers off by default)."""

from __future__ import annotations

import csv
import io
import os
from typing import Any

from keprix.discovery.models import (
    AdapterHealth,
    AdapterHealthStatus,
    AdapterManifest,
    DiscoverLimits,
    DiscoverQuery,
    FieldProvenance,
    LeadCandidate,
)

SCRAPE_REFUSAL = (
    "Keprix will not scrape Instagram, Facebook, TikTok, or LinkedIn by default. "
    "Scraping those platforms often violates their Terms of Service. "
    "Use the official API adapters (linkedin_api, meta_graph, tiktok_api) when "
    "credentials are configured, or import a platform export via social_csv_export."
)


def _env(*names: str) -> str:
    for name in names:
        value = os.environ.get(name, "").strip()
        if value:
            return value
    return ""


def _resolve(workspace_id: str | None, *names: str) -> str:
    if workspace_id:
        try:
            from keprix.crm.connections import resolve_any
            from keprix.crm.store import get_crm_store

            return resolve_any(*names, workspace_id=workspace_id, store=get_crm_store())
        except Exception:
            pass
    return _env(*names)


class _ApiStubBase:
    name = "social_stub"
    domain_packs = ["generic", "property", "health_social"]
    title = "Social API stub"
    env_keys: tuple[str, ...] = ()
    licence_ref = ""
    docs_path = "docs/features/social-discovery-api-first.md"
    feature_flag: str | None = None
    workspace_flag_id: str | None = None

    def _flag_on(self, workspace_id: str | None = None) -> bool:
        if not self.feature_flag and not self.workspace_flag_id:
            return True
        if workspace_id and self.workspace_flag_id:
            try:
                from keprix.crm.connections import workspace_flag_enabled
                from keprix.crm.store import get_crm_store

                if workspace_flag_enabled(get_crm_store(), workspace_id, self.workspace_flag_id):
                    return True
            except Exception:
                pass
        if self.feature_flag:
            return os.environ.get(self.feature_flag, "0").strip().lower() in {"1", "true", "yes", "on"}
        return False

    def _creds(self, workspace_id: str | None = None) -> dict[str, str]:
        return {k: _resolve(workspace_id, k) for k in self.env_keys}

    @property
    def manifest(self) -> AdapterManifest:
        return AdapterManifest(
            name=self.name,
            title=self.title,
            description=f"API-first stub for {self.name}. Scrapers remain feature-flagged off.",
            licence_ref=self.licence_ref,
            source_licence="Official platform API terms when configured",
            permitted_purpose="org_page_lead_review",
            contact_use_eligible=False,
            outreach_allowed=False,
            rate_limit_per_minute=10,
            domain_packs=list(self.domain_packs),
            requires_env=list(self.env_keys),
            feature_flag=self.feature_flag,
            experimental=False,
            docs_path=self.docs_path,
        )

    def _credentials(self, workspace_id: str | None = None) -> dict[str, str]:
        return self._creds(workspace_id)

    def health(self, workspace_id: str | None = None) -> AdapterHealth:
        creds = self._credentials(workspace_id)
        configured = all(bool(creds.get(k)) for k in self.env_keys) if self.env_keys else False
        if not configured:
            return AdapterHealth(
                name=self.name,
                status=AdapterHealthStatus.NOT_CONFIGURED,
                message=(
                    f"{self.name} credentials missing. Configure under /crm/settings Connections. "
                    f"{SCRAPE_REFUSAL} Required: {', '.join(self.env_keys)}"
                ),
                configured=False,
                enabled=True,
                details={
                    "required_env": list(self.env_keys),
                    "configure_path": "/crm/settings#connections",
                },
            )
        return AdapterHealth(
            name=self.name,
            status=AdapterHealthStatus.HEALTHY,
            message=f"{self.name} credentials present (API path only)",
            configured=True,
            enabled=True,
            details={"required_env": list(self.env_keys)},
        )

    def cost_forecast(self, query: DiscoverQuery, limits: DiscoverLimits) -> dict[str, Any]:
        return {"units": float(min(limits.max_results, 25)), "currency": "api_calls"}

    def discover(self, query: DiscoverQuery, limits: DiscoverLimits) -> list[LeadCandidate]:
        health = self.health()
        if health.status == AdapterHealthStatus.NOT_CONFIGURED:
            raise RuntimeError(health.message)

        # Fake configured path maps public org page / lead-gen style fields.
        # Real Marketing API sync is Nice (deferred) when owner provides app.
        fake_payload = query.params.get("api_payload") or query.params.get("org_pages") or []
        if isinstance(fake_payload, dict):
            fake_payload = [fake_payload]
        out: list[LeadCandidate] = []
        for idx, item in enumerate(fake_payload):
            if not isinstance(item, dict):
                continue
            company = item.get("name") or item.get("page_name") or item.get("organization")
            external_id = str(item.get("id") or item.get("page_id") or f"{self.name}-{idx}")
            email = item.get("email") or item.get("lead_email")
            url = item.get("url") or item.get("permalink")
            out.append(
                LeadCandidate(
                    company=str(company) if company else None,
                    contacts=[{"name": item.get("contact_name"), "email": email}] if email or item.get("contact_name") else [],
                    urls=[str(url)] if url else [],
                    geo={},
                    source=self.name,
                    external_id=external_id,
                    raw=dict(item),
                    score_hint=0.6,
                    emails=[str(email)] if email else [],
                    domain_pack=query.domain_pack or "generic",
                    provenance=[
                        FieldProvenance(field="company", source=self.name, external_id=external_id)
                    ],
                )
            )
            if len(out) >= limits.max_results:
                break
        if not out and query.text:
            # Configured but empty payload: return zero candidates (honest), not fabricated leads.
            return []
        return out


class LinkedInApiAdapter(_ApiStubBase):
    name = "linkedin_api"
    title = "LinkedIn Marketing / org pages API"
    env_keys = ("LINKEDIN_CLIENT_ID", "LINKEDIN_CLIENT_SECRET")
    licence_ref = "https://www.linkedin.com/legal/l/api-terms-of-use"
    feature_flag = "KEPRIX_LINKEDIN_API"
    workspace_flag_id = "linkedin_api_enabled"
    required_scopes = ("r_organization_social", "r_ads", "r_liteprofile")

    def health(self, workspace_id: str | None = None) -> AdapterHealth:
        base = super().health(workspace_id)
        details = dict(base.details or {})
        details["required_scopes"] = list(self.required_scopes)
        scopes = _resolve(workspace_id, "LINKEDIN_SCOPES") or ""
        missing = [s for s in self.required_scopes if s not in scopes.split()]
        if base.configured and missing and scopes:
            return AdapterHealth(
                name=self.name,
                status=AdapterHealthStatus.NOT_CONFIGURED,
                message=f"LinkedIn connected but missing scopes: {', '.join(missing)}",
                configured=False,
                enabled=True,
                details={**details, "missing_scopes": missing},
            )
        if not base.configured:
            details["setup"] = "Configure LinkedIn client id/secret under /crm/settings Connections."
            details["configure_path"] = "/crm/settings#connections"
        return AdapterHealth(
            name=base.name,
            status=base.status,
            message=base.message,
            configured=base.configured,
            enabled=base.enabled,
            details=details,
        )

    def sync_org_leads(self, query: DiscoverQuery, limits: DiscoverLimits) -> list[LeadCandidate]:
        """Production path when credentials present: map official payload to LeadCandidate."""
        return self.discover(query, limits)


class MetaGraphAdapter(_ApiStubBase):
    name = "meta_graph"
    title = "Meta Graph API (Facebook / Instagram)"
    env_keys = ("META_APP_ID", "META_APP_SECRET")
    licence_ref = "https://developers.facebook.com/policy/"
    feature_flag = "KEPRIX_META_GRAPH_API"
    workspace_flag_id = "meta_graph_api_enabled"
    required_scopes = ("pages_read_engagement", "leads_retrieval")

    def health(self) -> AdapterHealth:
        base = super().health()
        details = dict(base.details or {})
        details["required_scopes"] = list(self.required_scopes)
        return AdapterHealth(
            name=base.name,
            status=base.status,
            message=base.message,
            configured=base.configured,
            enabled=base.enabled,
            details=details,
        )


class TikTokApiAdapter(_ApiStubBase):
    name = "tiktok_api"
    title = "TikTok Marketing / Business API"
    env_keys = ("TIKTOK_APP_ID", "TIKTOK_APP_SECRET")
    licence_ref = "https://ads.tiktok.com/marketing_api/docs"
    feature_flag = "KEPRIX_TIKTOK_API"
    workspace_flag_id = "tiktok_api_enabled"
    required_scopes = ("user.info.basic", "video.list")

    def health(self) -> AdapterHealth:
        base = super().health()
        details = dict(base.details or {})
        details["required_scopes"] = list(self.required_scopes)
        return AdapterHealth(
            name=base.name,
            status=base.status,
            message=base.message,
            configured=base.configured,
            enabled=base.enabled,
            details=details,
        )


class SocialCsvExportAdapter:
    """Import social ads / lead-gen CSV exports (no scrape)."""

    name = "social_csv_export"
    domain_packs = ["generic", "property", "health_social"]

    @property
    def manifest(self) -> AdapterManifest:
        return AdapterManifest(
            name=self.name,
            title="Social ads CSV export import",
            description="Import lead-gen form / ads manager CSV exports. No scraping.",
            licence_ref="operator-export",
            source_licence="Operator-exported platform CSV; operator responsible for lawful basis",
            permitted_purpose="lead_import_review",
            contact_use_eligible=False,
            outreach_allowed=False,
            rate_limit_per_minute=60,
            domain_packs=list(self.domain_packs),
            docs_path="docs/features/social-discovery-api-first.md",
        )

    def health(self) -> AdapterHealth:
        return AdapterHealth(
            name=self.name,
            status=AdapterHealthStatus.HEALTHY,
            message="Social CSV export import ready",
            configured=True,
            enabled=True,
        )

    def cost_forecast(self, query: DiscoverQuery, limits: DiscoverLimits) -> dict[str, Any]:
        rows = query.params.get("rows") or []
        return {"units": float(min(len(rows) if rows else limits.max_results, limits.max_results)), "currency": "rows"}

    def discover(self, query: DiscoverQuery, limits: DiscoverLimits) -> list[LeadCandidate]:
        # Reuse CSV adapter mapping with social-ish aliases.
        from keprix.discovery.adapters.csv_import import CsvDiscoveryAdapter

        params = dict(query.params)
        if params.get("csv_text") and not params.get("rows"):
            reader = csv.DictReader(io.StringIO(str(params["csv_text"])))
            params["rows"] = [dict(r) for r in reader]
        nested = DiscoverQuery(
            text=query.text,
            params=params,
            domain_pack=query.domain_pack,
            workspace_id=query.workspace_id,
        )
        candidates = CsvDiscoveryAdapter().discover(nested, limits)
        for cand in candidates:
            cand.source = self.name
            cand.raw = {**(cand.raw or {}), "import_kind": "social_csv_export"}
        return candidates


def scrape_refusal_payload(platform: str | None = None) -> dict[str, Any]:
    return {
        "refused": True,
        "error_code": "social_scrape_refused",
        "platform": platform,
        "message": SCRAPE_REFUSAL,
        "api_adapters": ["linkedin_api", "meta_graph", "tiktok_api", "social_csv_export"],
        "docs": "docs/features/social-discovery-api-first.md",
    }
