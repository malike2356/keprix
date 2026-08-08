# Soft Wall list enroll + viCal booking SoT

## List enroll preflight

- GUI: `/outreach/lists` → **Soft Wall enroll** opens preflight modal
- API:
  - `POST /api/outreach/lists/{id}/enroll-preflight` `{ sequence_id, campaign_id? }`
  - `POST /api/outreach/lists/{id}/enroll` `{ sequence_id, audience_hash, force?, approval_id? }`
- Counts: eligible, suppressed, contactability_deny, duplicate, ambiguous, ineligible
- Soft Wall gate `approve_list_enroll` captures `audience_hash`; membership changes invalidate prior approval
- Skipped members deep-link to `/outreach/suppressions` and `/outreach/contactability`
- Eligible enrolls also enqueue CRM outbox rows (`soft_wall_enroll`) for visibility

## viCal Soft Wall booking SoT

- On viCal booking **confirmed**, `soft_wall_handoff_on_vical_confirmed` updates Soft Wall lead stage to `booked`, links Soft Wall booking notes `vical:{id}`, and updates CRM lead stage when present
- Soft Wall `/outreach/bookings` prefers viCal hub mesh links; Soft Wall-only create remains a fallback
- viCal hub already exposes mesh related links (`MeshRelatedLinks`)

## Related

- Soft Wall safety: [soft-wall-safety.md](soft-wall-safety.md)
- viCal: [vical.md](vical.md)
