# Agentic CRM troubleshooting

CRM lives under `/crm` with section tabs (Pipeline, Leads, Contacts, Discover, Jobs, Soft Wall-related delivery surfaces, and more).

## Typical flow

1. Discover or import leads (`/crm/discover`, `/crm/leads`).
2. Enrich and qualify (`/crm/enrich`, licensed enrich settings).
3. Enroll into outreach sequences (`/outreach` Soft Wall path).
4. Approve outbound on `/outreach/approvals`.

## Symptom: CRM tab or overview card does not navigate

**Fix:** Hard-refresh `/crm`. See [UI navigation](ui-navigation.md).

## Symptom: Discover or enrich job stuck

**Fix:**

1. Open `/crm/jobs` and inspect the job status/error.
2. Confirm API keys / licensed enrich settings under `/crm/settings`.
3. Check deliverability and contactability before mass enroll.

## Symptom: Soft Wall blocks CRM-driven outreach

**Expected.** High-risk sends require approval. Use `/outreach/approvals`.

## Related docs

- [Agentic CRM](../features/agentic-crm.md)
- [CRM compliance](../features/crm-compliance.md)
- [CRM integrations](../features/crm-integrations.md)
- [Licensed enrichment](../features/crm-licensed-enrichment.md)
