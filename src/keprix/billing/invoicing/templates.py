"""HTML invoice templates."""

from __future__ import annotations

from keprix.billing.config_loader import load_billing_config


def render_invoice_html(
    *,
    invoice_number: str,
    customer_name: str,
    customer_email: str,
    description: str,
    subtotal_minor: int,
    tax_minor: int,
    total_minor: int,
    currency: str,
    status: str,
) -> str:
    cfg = load_billing_config()
    product = cfg.product if cfg else None
    company = product.company if product else "Keprix"
    address = product.company_address if product else ""
    vat = product.vat_number if product else ""

    def money(amount: int) -> str:
        return f"{currency.upper()} {amount / 100:.2f}"

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Invoice {invoice_number}</title></head>
<body style="font-family: sans-serif; max-width: 720px; margin: 2rem auto;">
  <h1>INVOICE</h1>
  <p><strong>{company}</strong><br>{address}<br>VAT: {vat or 'N/A'}</p>
  <p><strong>Invoice #:</strong> {invoice_number}<br><strong>Status:</strong> {status.upper()}</p>
  <h3>Bill to</h3>
  <p>{customer_name}<br>{customer_email}</p>
  <table width="100%" cellpadding="8" cellspacing="0" border="1" style="border-collapse: collapse;">
    <tr><th align="left">Description</th><th align="right">Amount</th></tr>
    <tr><td>{description}</td><td align="right">{money(subtotal_minor)}</td></tr>
    <tr><td>Subtotal</td><td align="right">{money(subtotal_minor)}</td></tr>
    <tr><td>Tax</td><td align="right">{money(tax_minor)}</td></tr>
    <tr><td><strong>Total</strong></td><td align="right"><strong>{money(total_minor)}</strong></td></tr>
  </table>
</body></html>"""
