"""Safety checks for opportunity engine operations."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse

from keprix.opportunity.citations import list_citations

_COMPLIANCE_KEYWORDS = re.compile(
    r"\b(guaranteed returns?|cure|legal advice|financial advice|medical advice)\b",
    re.IGNORECASE,
)
_LOGIN_PATH_HINTS = re.compile(r"/(login|signin|sign-in|auth)\b", re.IGNORECASE)


class SafetyViolation(Exception):
    """Raised when a safety rule is violated."""


def check_no_fabricated_citations(*, opportunity_id: str, claimed_urls: list[str]) -> None:
    known = {cite.url for cite in list_citations(opportunity_id)}
    for url in claimed_urls:
        if url and url not in known:
            raise SafetyViolation(f"Unsupported citation URL: {url}")


def check_no_login_scraping(url: str) -> None:
    parsed = urlparse(url)
    path = parsed.path or ""
    if _LOGIN_PATH_HINTS.search(path):
        raise SafetyViolation("Scraping behind login pages is not allowed")


def check_personal_data_collection(
    *,
    integration_configured: bool,
    lawful_basis: str | None,
) -> None:
    if not integration_configured:
        raise SafetyViolation(
            "Personal data collection requires a connected integration and lawful basis",
        )
    if not lawful_basis:
        raise SafetyViolation("Lawful basis must be configured before collecting personal data")


def check_ad_launch(*, human_approved: bool) -> None:
    if not human_approved:
        raise SafetyViolation("Ad launch requires explicit human approval")


def check_no_competitor_impersonation(text: str) -> None:
    lowered = text.lower()
    if "impersonat" in lowered or "pretend to be" in lowered:
        raise SafetyViolation("Competitor impersonation is not allowed")


def check_claims_supported(*, opportunity_id: str, text: str, require_citation: bool = False) -> None:
    if not require_citation:
        return
    citations = list_citations(opportunity_id)
    if not citations and len(text) > 200:
        raise SafetyViolation("Claims must be supported by citations when research is cited")


def check_compliance_warnings(text: str) -> list[str]:
    warnings: list[str] = []
    if _COMPLIANCE_KEYWORDS.search(text):
        warnings.append(
            "Content may include medical, legal, or financial promises; add compliance review.",
        )
    return warnings


def validate_research_url(url: str) -> str:
    check_no_login_scraping(url)
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise SafetyViolation("Research URLs must use http or https")
    if not parsed.netloc:
        raise SafetyViolation("Research URL must have a host")
    return url


def run_content_safety_checks(
    *,
    opportunity_id: str,
    text: str,
    require_citations: bool = False,
) -> dict[str, Any]:
    check_no_competitor_impersonation(text)
    check_claims_supported(opportunity_id=opportunity_id, text=text, require_citation=require_citations)
    warnings = check_compliance_warnings(text)
    return {"ok": True, "warnings": warnings}
