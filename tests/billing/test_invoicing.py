"""Tests for invoice HTML generation."""

from __future__ import annotations

from keprix.billing.invoicing.generator import generate_invoice_html


def test_invoice_html_contains_totals():
    html = generate_invoice_html(
        invoice_number="INV-001",
        customer_name="Ada Lovelace",
        customer_email="ada@example.com",
        description="Pro plan (monthly)",
        subtotal=4900,
        tax_amount=980,
        total=5880,
        currency="gbp",
        status="paid",
    )
    assert "INV-001" in html
    assert "Ada Lovelace" in html
    assert "GBP 58.80" in html
    assert "PAID" in html.upper() or "paid" in html
