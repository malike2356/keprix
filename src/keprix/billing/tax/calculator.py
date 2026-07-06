"""VAT and sales tax calculation."""

from __future__ import annotations

from dataclasses import dataclass

from keprix.billing.config_loader import load_billing_config
from keprix.billing.tax.rates import EU_VAT_RATES, match_tax_region
from keprix.billing.tax.validator import validate_vat_id


@dataclass
class TaxResult:
    rate: float
    amount: int
    label: str


def calculate_tax(customer_country: str, customer_vat_id: str | None, amount: int) -> TaxResult:
    cfg = load_billing_config()
    if cfg is None or amount <= 0:
        return TaxResult(rate=0.0, amount=0, label="No tax applied")

    region = match_tax_region(customer_country, cfg.tax.regions)
    if region is None or region.rule == "none":
        return TaxResult(rate=0.0, amount=0, label="No tax applied")

    if region.rule == "b2b_reverse" and customer_vat_id:
        if validate_vat_id(customer_vat_id, region.vat_validation):
            return TaxResult(rate=0.0, amount=0, label="VAT reverse charge (B2B)")

    if region.rate is not None and region.rate > 0:
        tax = round(amount * region.rate)
        return TaxResult(rate=region.rate, amount=tax, label=f"VAT {region.rate * 100:.0f}%")

    if region.code == "EU":
        local_rate = EU_VAT_RATES.get(customer_country.upper(), 0.0)
        tax = round(amount * local_rate)
        return TaxResult(rate=local_rate, amount=tax, label=f"VAT {local_rate * 100:.0f}% ({customer_country})")

    return TaxResult(rate=0.0, amount=0, label="No tax applied")
