# Soft Wall safety operator surfaces

Workspace Soft Wall safety pages under `/outreach/*` (tabs on Sales engagement):

| Page | Route | Purpose |
| --- | --- | --- |
| Deliverability | `/outreach/deliverability` | Sender domains, SPF/DKIM/DMARC honesty, bounce/complaint/unsub rates, cold-send Soft Wall block |
| Outbox | `/outreach/outbox` | Pending / failed / dead_letter; Soft Wall retry keeps idempotency key; cancel pending |
| Suppressions | `/outreach/suppressions` | Add / undo (Soft Wall) / bulk preview+import / CSV export |
| Contactability | `/outreach/contactability` | Found != contactable; allow/deny/needs_review by channel and purpose |
| Merges | `/outreach/merges` | Provenance diff; Soft Wall apply; reject keeps both records |
| Safety settings | `/outreach/settings` | Kill switches (Soft Wall to disable); cadence notes |

## APIs

All workspace-scoped under `/api/crm/*`:

- `GET /deliverability` (includes rates, thresholds, `soft_wall_block_cold_send`)
- `PUT /deliverability/sender-readiness`
- `GET /outbox`, `POST /outbox/{id}/retry`, `POST /outbox/{id}/cancel`
- `GET|POST /suppressions`, `DELETE /suppressions/{id}`, `POST /suppressions/bulk`
- `GET|PUT /contactability`
- `GET /merges`, `POST /merges/{id}/apply`, `POST /merges/{id}/reject`
- `GET|PUT /kill-switches`

## Soft Wall gates

`outbox_retry`, `suppress_undo`, `suppress_bulk_import`, `merge_identity`, `kill_switch_off`, `budget_raise`.

## Contactability vs consent

Contactability is a purpose/channel decision (may we contact for outreach?).
Consent and suppressions are compliance records. Discovery never auto-allows contact.

## Related

- CRM Soft Wall: `src/keprix/crm/soft_wall.py`
- Inventory: `docs/architecture/operator-gui-gap-inventory.md`
