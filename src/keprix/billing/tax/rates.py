"""Tax region matching and EU VAT MOSS rates."""

from __future__ import annotations

from keprix.billing.schema import TaxRegionConfig

EU_COUNTRIES = {
    "AT",
    "BE",
    "BG",
    "CY",
    "CZ",
    "DE",
    "DK",
    "EE",
    "ES",
    "FI",
    "FR",
    "GR",
    "HR",
    "HU",
    "IE",
    "IT",
    "LT",
    "LU",
    "LV",
    "MT",
    "NL",
    "PL",
    "PT",
    "RO",
    "SE",
    "SI",
    "SK",
}

EU_VAT_RATES: dict[str, float] = {
    "DE": 0.19,
    "FR": 0.20,
    "IE": 0.23,
    "NL": 0.21,
    "ES": 0.21,
    "IT": 0.22,
    "SE": 0.25,
}


def match_tax_region(country_code: str, regions: list[TaxRegionConfig]) -> TaxRegionConfig | None:
    code = country_code.upper()
    for region in regions:
        if region.code == code:
            return region
    if code in EU_COUNTRIES:
        for region in regions:
            if region.code == "EU":
                return region
    for region in regions:
        if region.code == "ROW":
            return region
    return regions[0] if regions else None
