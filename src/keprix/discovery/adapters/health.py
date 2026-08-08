"""Health / social care vertical adapters (orgs and professionals only; no patient data)."""

from __future__ import annotations

import os
from typing import Any

from keprix.discovery.adapters.csv_import import CsvDiscoveryAdapter
from keprix.discovery.adapters.web_directory import WebDirectoryAdapter
from keprix.discovery.models import (
    AdapterHealth,
    AdapterHealthStatus,
    AdapterManifest,
    DiscoverLimits,
    DiscoverQuery,
    FieldProvenance,
    LeadCandidate,
)

NO_PATIENT_DATA = (
    "Health/social care discovery is limited to organisations and professional contacts. "
    "Patient, service-user, or clinical personal data must never be imported."
)


class HealthCsvAdapter(CsvDiscoveryAdapter):
    name = "health_csv"
    domain_packs = ["health_social", "healthcare", "care"]

    @property
    def manifest(self) -> AdapterManifest:
        return AdapterManifest(
            name=self.name,
            title="Health / social care CSV",
            description=f"Care-provider and practitioner CSV import. {NO_PATIENT_DATA}",
            licence_ref="operator-supplied-data",
            source_licence="Operator-provided directory CSV; high-risk Soft Wall on enroll",
            permitted_purpose="care_provider_directory_review",
            allowed_fields=[
                "company",
                "company_number",
                "geo",
                "contacts",
                "emails",
                "phones",
                "urls",
            ],
            retention="workspace_policy",
            jurisdiction="UK",
            contact_use_eligible=False,
            outreach_allowed=False,
            rate_limit_per_minute=60,
            domain_packs=list(self.domain_packs),
            docs_path="docs/features/health-social-care-pack.md",
        )

    def discover(self, query: DiscoverQuery, limits: DiscoverLimits) -> list[LeadCandidate]:
        # Reject obvious patient-data columns.
        rows = query.params.get("rows") or []
        if isinstance(rows, list) and rows:
            headers = " ".join(str(k).lower() for k in (rows[0] or {}).keys())
            banned = ("nhs_number", "patient", "diagnosis", "medical_record", "dob", "date_of_birth")
            if any(b in headers for b in banned):
                raise RuntimeError(
                    "Refusing health CSV that appears to contain patient/clinical fields. "
                    + NO_PATIENT_DATA
                )
        q = DiscoverQuery(
            text=query.text,
            params=query.params,
            domain_pack=query.domain_pack or "health_social",
            workspace_id=query.workspace_id,
        )
        candidates = super().discover(q, limits)
        for cand in candidates:
            cand.source = self.name
            cand.domain_pack = "health_social"
            cand.notes = (cand.notes or "") + f" {NO_PATIENT_DATA}"
        return candidates


class CqcApiAdapter:
    name = "cqc_api"
    domain_packs = ["health_social", "care"]

    @property
    def manifest(self) -> AdapterManifest:
        return AdapterManifest(
            name=self.name,
            title="CQC public API (stub)",
            description=(
                "Stub for Care Quality Commission public directory data. "
                f"{NO_PATIENT_DATA}"
            ),
            licence_ref="https://www.cqc.org.uk/about-us/transparency/using-cqc-data",
            source_licence="CQC open data / API terms when configured",
            permitted_purpose="care_provider_directory_review",
            contact_use_eligible=False,
            outreach_allowed=False,
            rate_limit_per_minute=10,
            domain_packs=list(self.domain_packs),
            requires_env=["CQC_API_KEY"],
            docs_path="docs/features/health-social-care-pack.md",
        )

    def health(self) -> AdapterHealth:
        key = os.environ.get("CQC_API_KEY", "").strip()
        # Public CQC endpoints may not need a key; treat missing key as not_configured
        # until a live client is wired (honest stub).
        if not key and not os.environ.get("KEPRIX_CQC_PUBLIC_MODE"):
            return AdapterHealth(
                name=self.name,
                status=AdapterHealthStatus.NOT_CONFIGURED,
                message=(
                    "CQC API not configured. Set CQC_API_KEY or KEPRIX_CQC_PUBLIC_MODE=1 "
                    "when a live client is approved. Use health_csv meanwhile."
                ),
                configured=False,
                enabled=True,
            )
        return AdapterHealth(
            name=self.name,
            status=AdapterHealthStatus.HEALTHY,
            message="CQC stub configured (directory orgs only)",
            configured=True,
            enabled=True,
        )

    def cost_forecast(self, query: DiscoverQuery, limits: DiscoverLimits) -> dict[str, Any]:
        return {"units": float(min(limits.max_results, 25)), "currency": "api_calls"}

    def discover(self, query: DiscoverQuery, limits: DiscoverLimits) -> list[LeadCandidate]:
        health = self.health()
        if health.status == AdapterHealthStatus.NOT_CONFIGURED:
            raise RuntimeError(health.message)
        payload = query.params.get("providers") or query.params.get("api_payload") or []
        if isinstance(payload, dict):
            payload = [payload]
        out: list[LeadCandidate] = []
        for idx, item in enumerate(payload):
            if not isinstance(item, dict):
                continue
            # Explicitly drop patient-like keys if present.
            safe = {
                k: v
                for k, v in item.items()
                if str(k).lower()
                not in {"patient", "nhs_number", "diagnosis", "medical_record", "dob"}
            }
            name = safe.get("name") or safe.get("organisation") or safe.get("provider_name")
            cqc_id = safe.get("cqc_id") or safe.get("location_id") or safe.get("id")
            external_id = str(cqc_id or f"cqc-{idx}")
            out.append(
                LeadCandidate(
                    company=str(name) if name else None,
                    company_number=str(cqc_id) if cqc_id else None,
                    contacts=[
                        {
                            "name": safe.get("contact_name"),
                            "email": safe.get("email"),
                            "phone": safe.get("phone"),
                        }
                    ]
                    if safe.get("email") or safe.get("phone") or safe.get("contact_name")
                    else [],
                    urls=[str(safe["url"])] if safe.get("url") else [],
                    geo={
                        k: safe[k]
                        for k in ("region", "locality", "postcode", "local_authority")
                        if safe.get(k)
                    },
                    source=self.name,
                    external_id=external_id,
                    raw=safe,
                    score_hint=0.65,
                    emails=[str(safe["email"])] if safe.get("email") else [],
                    phones=[str(safe["phone"])] if safe.get("phone") else [],
                    domain_pack="health_social",
                    notes=NO_PATIENT_DATA,
                    provenance=[
                        FieldProvenance(field="company", source=self.name, external_id=external_id),
                        FieldProvenance(
                            field="company_number", source=self.name, external_id=external_id
                        ),
                    ],
                )
            )
            if len(out) >= limits.max_results:
                break
        return out


class DirectoryWebHealthAdapter(WebDirectoryAdapter):
    """Reuse web_directory with health_social query templates."""

    name = "directory_web"
    domain_packs = ["health_social", "care", "healthcare"]

    @property
    def manifest(self) -> AdapterManifest:
        base = super().manifest
        return AdapterManifest(
            name=self.name,
            title="Health directory web search",
            description=f"Web directory discovery for care providers. {NO_PATIENT_DATA}",
            licence_ref=base.licence_ref,
            source_licence=base.source_licence,
            permitted_purpose="care_provider_directory_review",
            allowed_fields=list(base.allowed_fields),
            retention=base.retention,
            jurisdiction="UK",
            contact_use_eligible=False,
            outreach_allowed=False,
            rate_limit_per_minute=base.rate_limit_per_minute,
            domain_packs=list(self.domain_packs),
            docs_path="docs/features/health-social-care-pack.md",
        )

    def discover(self, query: DiscoverQuery, limits: DiscoverLimits) -> list[LeadCandidate]:
        q = DiscoverQuery(
            text=query.text,
            params=query.params,
            domain_pack=query.domain_pack or "health_social",
            workspace_id=query.workspace_id,
        )
        candidates = super().discover(q, limits)
        for cand in candidates:
            cand.source = self.name
            cand.domain_pack = "health_social"
            cand.notes = ((cand.notes or "") + " " + NO_PATIENT_DATA).strip()
        return candidates
