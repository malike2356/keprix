"""VAT ID validation (format checks; live VIES/HMRC hooks are extension-specific)."""

from __future__ import annotations

import re


_VAT_PATTERNS = {
    "GB": re.compile(r"^GB[0-9]{9}([0-9]{3})?$"),
    "IE": re.compile(r"^IE[0-9]{7}[A-Z]{1,2}$"),
    "DE": re.compile(r"^DE[0-9]{9}$"),
}


def validate_vat_id(vat_id: str, provider: str) -> bool:
    cleaned = vat_id.replace(" ", "").upper()
    if not cleaned:
        return False
    if provider == "none":
        return len(cleaned) >= 8
    country = cleaned[:2]
    pattern = _VAT_PATTERNS.get(country)
    if pattern is None:
        return len(cleaned) >= 8 and cleaned[:2].isalpha()
    return bool(pattern.match(cleaned))
