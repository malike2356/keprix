"""Billing history helpers for portal invoice listings."""

from __future__ import annotations

from typing import Any

from keprix.billing.store import get_billing_store


async def list_billing_history(user_id: str) -> list[dict[str, Any]]:
    invoices = await get_billing_store().list_invoices(user_id)
    return sorted(invoices, key=lambda row: row.get("created_at", ""), reverse=True)


async def get_invoice_for_user(user_id: str, invoice_id: str) -> dict[str, Any] | None:
    invoice = await get_billing_store().get_invoice(invoice_id)
    if invoice is None or invoice.get("user_id") != user_id:
        return None
    return invoice
