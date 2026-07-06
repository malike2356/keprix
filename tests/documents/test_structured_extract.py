"""Structured extraction tests."""

import pytest

from keprix.documents.structured_extract import extract_structured


def test_invoice_schema_validates() -> None:
    text = "Vendor: Acme Ltd\nInvoice: INV-100\nTotal: $42.50\nDue: 2026-08-01"
    result = extract_structured(text, "invoice")
    assert result["vendor"] == "Acme Ltd"
    assert result["invoice_number"]
    assert result["total_amount"]


def test_unknown_schema_raises() -> None:
    with pytest.raises(ValueError):
        extract_structured("hello", "not-a-schema")
