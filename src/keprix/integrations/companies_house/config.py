"""Companies House env / capability helpers."""

from __future__ import annotations

import os

API_BASE = "https://api.company-information.service.gov.uk"
PUBLIC_COMPANY_BASE = "https://find-and-update.company-information.service.gov.uk/company"
API_HOST = "api.company-information.service.gov.uk"

ENV_API_KEY = "COMPANIES_HOUSE_API_KEY"
ENV_ENABLED = "KEPRIX_COMPANIES_HOUSE_ENABLED"


def is_enabled() -> bool:
    raw = os.getenv(ENV_ENABLED, "1").strip().lower()
    return raw not in {"0", "false", "no", "off"}


def get_api_key() -> str:
    return os.getenv(ENV_API_KEY, "").strip()


def is_configured() -> bool:
    return bool(get_api_key())


def status_payload() -> dict:
    return {
        "enabled": is_enabled(),
        "configured": is_configured(),
        "api_key_set": is_configured(),
        "api_base": API_BASE,
        "docs": "https://developer.company-information.service.gov.uk/",
    }


def ensure_egress_allowlist(product_id: str = "keprix") -> None:
    """Merge Companies House API host into the product egress allowlist."""
    from keprix.security.egress_policy import get_egress_policy

    policy = get_egress_policy()
    snap = policy.snapshot().get(product_id)
    hosts = set(snap.get("allowed_hosts") or []) if snap else set()
    hosts.add(API_HOST)
    default_deny = bool(snap.get("default_deny", True)) if snap else True
    policy.load_product(product_id, allowed_hosts=hosts, default_deny=default_deny)


def public_company_url(company_number: str) -> str:
    number = (company_number or "").strip().upper()
    return f"{PUBLIC_COMPANY_BASE}/{number}"
