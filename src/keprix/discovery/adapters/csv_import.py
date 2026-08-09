"""CSV discovery adapter (map columns via sheet_preprocess or auto)."""

from __future__ import annotations

import csv
import io
import json
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

try:
    from keprix.crm.ingestion.canonical import ALIASES, map_headers, normalize_header
except Exception:  # pragma: no cover - soft fallback
    ALIASES = {}
    map_headers = None  # type: ignore[assignment]
    normalize_header = None  # type: ignore[assignment]


_COLUMN_ALIASES: dict[str, tuple[str, ...]] = {
    "company": ("company", "company_name", "organisation", "organization", "business", "name"),
    "company_number": ("company_number", "crn", "companies_house_number", "cqc_id", "registration"),
    "email": ("email", "email_address", "contact_email", "work_email"),
    "phone": ("phone", "telephone", "mobile", "contact_phone"),
    "url": ("url", "website", "domain", "homepage"),
    "contact_name": ("contact", "contact_name", "full_name", "person"),
    "locality": ("city", "town", "locality", "region", "location"),
    "postcode": ("postcode", "postal_code", "zip"),
}

# Map discovery logical fields onto canonical ingestion keys.
_CANONICAL_TO_LOGICAL = {
    "company_name": "company",
    "email": "email",
    "phone": "phone",
    "website": "url",
    "name": "contact_name",
    "locality": "locality",
}


def _norm_header(value: str) -> str:
    if normalize_header is not None:
        return normalize_header(value)
    return "".join(ch if ch.isalnum() else "_" for ch in value.strip().lower()).strip("_")


def _pick(row: dict[str, Any], *keys: str) -> Any:
    lower_map = {_norm_header(k): v for k, v in row.items()}
    for key in keys:
        if key in lower_map and lower_map[key] not in (None, ""):
            return lower_map[key]
    return None


def _resolve_schema(user_schema: dict[str, Any] | None) -> dict[str, str]:
    """Map logical fields -> CSV column names from user_schema or empty (auto)."""
    if not user_schema:
        return {}
    # Accept {company: "Org Name"} or sheet_preprocess-style {columns: {.. role ..}}
    if "columns" in user_schema and isinstance(user_schema["columns"], dict):
        role_to_col: dict[str, str] = {}
        for col, spec in user_schema["columns"].items():
            role = spec.get("role") if isinstance(spec, dict) else spec
            role_s = str(role or "").lower()
            if role_s in {"company_name", "company"}:
                role_to_col["company"] = col
            elif role_s in {"contact_email", "email"}:
                role_to_col["email"] = col
            elif role_s in {"contact_phone", "phone"}:
                role_to_col["phone"] = col
            elif role_s in {"identity", "company_number"}:
                role_to_col["company_number"] = col
            elif role_s == "url":
                role_to_col["url"] = col
            elif role_s in {"contact_name", "name"}:
                role_to_col["contact_name"] = col
        return role_to_col
    return {str(k): str(v) for k, v in user_schema.items() if v}


class CsvDiscoveryAdapter:
    name = "csv"
    domain_packs = ["generic", "property", "health_social"]

    @property
    def manifest(self) -> AdapterManifest:
        return AdapterManifest(
            name=self.name,
            title="CSV upload discovery",
            description="Map CSV rows to LeadCandidates via auto headers or sheet_preprocess user_schema.",
            licence_ref="operator-supplied-data",
            source_licence="Operator-provided CSV; operator responsible for lawful basis",
            permitted_purpose="lead_list_import_review",
            contact_use_eligible=False,
            outreach_allowed=False,
            rate_limit_per_minute=60,
            domain_packs=list(self.domain_packs),
        )

    def health(self) -> AdapterHealth:
        return AdapterHealth(
            name=self.name,
            status=AdapterHealthStatus.HEALTHY,
            message="CSV adapter ready (no external credentials)",
            configured=True,
            enabled=True,
        )

    def cost_forecast(self, query: DiscoverQuery, limits: DiscoverLimits) -> dict[str, Any]:
        rows = query.params.get("rows") or []
        return {"units": float(min(len(rows), limits.max_results)), "currency": "rows"}

    def discover(self, query: DiscoverQuery, limits: DiscoverLimits) -> list[LeadCandidate]:
        rows = self._load_rows(query.params)
        schema = _resolve_schema(query.params.get("user_schema") or query.params.get("schema"))
        out: list[LeadCandidate] = []
        for idx, row in enumerate(rows):
            if not isinstance(row, dict):
                continue
            company = self._field(row, schema, "company")
            company_number = self._field(row, schema, "company_number")
            email = self._field(row, schema, "email")
            phone = self._field(row, schema, "phone")
            url = self._field(row, schema, "url")
            contact_name = self._field(row, schema, "contact_name")
            locality = self._field(row, schema, "locality")
            postcode = self._field(row, schema, "postcode")
            if not company and not email and not company_number:
                # Fall back to first non-empty cell as company.
                for value in row.values():
                    if value not in (None, ""):
                        company = str(value)
                        break
            if not company and not email:
                continue
            contacts: list[dict[str, Any]] = []
            if contact_name or email or phone:
                contacts.append(
                    {
                        "name": contact_name,
                        "email": email,
                        "phone": phone,
                    }
                )
            domain = None
            if url:
                domain = str(url).replace("https://", "").replace("http://", "").split("/")[0]
            elif email and "@" in str(email):
                domain = str(email).split("@", 1)[1]
            geo: dict[str, Any] = {}
            if locality:
                geo["locality"] = locality
            if postcode:
                geo["postcode"] = postcode
            external_id = str(company_number or email or f"csv-row-{idx}")
            out.append(
                LeadCandidate(
                    company=str(company) if company else None,
                    company_number=str(company_number) if company_number else None,
                    contacts=contacts,
                    urls=[str(url)] if url else [],
                    geo=geo,
                    source=self.name,
                    external_id=external_id,
                    raw=dict(row),
                    score_hint=0.55,
                    emails=[str(email)] if email else [],
                    phones=[str(phone)] if phone else [],
                    domain=domain,
                    domain_pack=query.domain_pack or "generic",
                    provenance=[
                        FieldProvenance(field="company", source=self.name, external_id=external_id)
                    ],
                )
            )
            if len(out) >= limits.max_results:
                break
        return out

    def _field(self, row: dict[str, Any], schema: dict[str, str], logical: str) -> Any:
        if logical in schema:
            col = schema[logical]
            # Match original or normalised header
            if col in row:
                return row.get(col)
            return _pick(row, _norm_header(col))
        # Prefer canonical SEO header map (Prompt 621) when available.
        if map_headers is not None:
            mapping = map_headers([str(h) for h in row.keys()])
            for header, canonical in mapping.items():
                if _CANONICAL_TO_LOGICAL.get(canonical) == logical:
                    value = row.get(header)
                    if value not in (None, ""):
                        return value
            # Also accept already-canonical keys via ALIASES reverse.
            for header, value in row.items():
                norm = _norm_header(str(header))
                canonical = ALIASES.get(norm)
                if canonical and _CANONICAL_TO_LOGICAL.get(canonical) == logical and value not in (None, ""):
                    return value
        aliases = _COLUMN_ALIASES.get(logical, (logical,))
        return _pick(row, *[_norm_header(a) for a in aliases])

    def _load_rows(self, params: dict[str, Any]) -> list[dict[str, Any]]:
        if isinstance(params.get("rows"), list):
            return list(params["rows"])
        csv_text = params.get("csv_text") or params.get("content") or ""
        if not csv_text and params.get("records_json"):
            raw = params["records_json"]
            data = json.loads(raw) if isinstance(raw, str) else raw
            if isinstance(data, list):
                return [r for r in data if isinstance(r, dict)]
        if not csv_text:
            return []
        reader = csv.DictReader(io.StringIO(str(csv_text)))
        return [dict(row) for row in reader]
