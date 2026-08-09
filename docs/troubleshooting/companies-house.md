# Companies House troubleshooting

## Symptom: Search returns nothing or key error

**Likely cause:** Missing or invalid Companies House Public Data API key, or feature disabled.

**Fix:**

1. Open `/settings/companies-house` (or Settings → Companies House) and save a valid key.
2. Retry search on `/companies-house` or `/outreach/companies-house`.
3. Confirm network egress allows `api.company-information.service.gov.uk` if you use egress controls (`/admin/network-egress`).

## Symptom: Import lead from registry fails

**Fix:** Use Outreach Companies House (`/outreach/companies-house`) so the import lands as an outreach lead. Confirm Soft Wall / workspace access afterward.

## Related docs

- [Companies House feature guide](../features/companies-house.md)
- [Soft Wall and outreach](soft-wall-and-outreach.md)
