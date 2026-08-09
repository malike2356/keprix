# Soft Wall and outreach troubleshooting

Workspace routes live under `/outreach`. Soft Wall means **approve-then-retry**: cold or high-risk sends do not leave the system until an operator approves them.

## Symptom: Outreach overview shows Loading forever

**Likely cause:** API error or missing workspace context.

**Fix:**

1. Open browser network tab; check `/api/outreach/overview` and `/api/outreach/control`.
2. Confirm you are signed in and have access to the Default (or selected) workspace.
3. Check backend health and logs for `outreach` errors.

## Symptom: Cannot send campaign / sequence steps

**Likely cause:** Soft Wall gate, deliverability block, suppression, or pause control.

**Fix:**

1. Open `/outreach/approvals` and approve or reject pending Soft Wall items.
2. Check `/outreach/deliverability` and `/outreach/suppressions`.
3. On Overview, confirm outreach is not paused (`Pause outreach` / control center).
4. Process due steps only after approvals exist.

## Symptom: Companies House import from outreach fails

**Fix:** See [Companies House](companies-house.md). Prefer `/outreach/companies-house` for lead import.

## Symptom: Channel shortcuts unclear

Use `/outreach/channels` as a hub. Each card jumps to Approvals, Review Gateway, Companies House, or Mailbox. Detail: [UI navigation](ui-navigation.md).

## Related docs

- [Soft Wall safety](../features/soft-wall-safety.md)
- [Soft Wall enroll + viCal](../features/soft-wall-enroll-vical.md)
- [Agentic CRM](../features/agentic-crm.md)
- [Email](../features/email.md)
