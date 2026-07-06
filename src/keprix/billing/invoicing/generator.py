"""Invoice HTML generation."""

from __future__ import annotations

from keprix.billing.invoicing.templates import render_invoice_html
from keprix.billing.tax.calculator import calculate_tax


def generate_invoice_html(
    *,
    invoice_number: str,
    customer_name: str,
    customer_email: str,
    description: str,
    subtotal: int,
    tax_amount: int | None = None,
    total: int | None = None,
    currency: str = "gbp",
    status: str = "paid",
    customer_country: str = "GB",
    customer_vat_id: str | None = None,
) -> str:
    if tax_amount is None:
        tax = calculate_tax(customer_country, customer_vat_id, subtotal)
        tax_amount = tax.amount
    if total is None:
        total = subtotal + (tax_amount or 0)
    return render_invoice_html(
        invoice_number=invoice_number,
        customer_name=customer_name,
        customer_email=customer_email,
        description=description,
        subtotal_minor=subtotal,
        tax_minor=tax_amount,
        total_minor=total,
        currency=currency,
        status=status,
    )
