# Visual CRM operator runbook (prompt 515)

## Publish / activate / pause

1. Open `/crm/workflows` and choose a sequence.
2. Open canvas at `/crm/workflows/{id}`.
3. Validate. Blocking issues (missing trigger/stop/approval) prevent publish.
4. Simulate (no external sends).
5. Publish. Active executions stay pinned to the published version snapshot.
6. Pause/activate Soft Wall sequence status from the workflows list when needed.

## Cancel / retry / human takeover

- Failed nodes: open `/crm/runs/{id}`, select the node, use inspector attempts/policy.
- Soft Wall approvals: `/crm` Soft Wall panel or `/crm/ops` waiting approvals.
- Human takeover: `/crm/inbox` claim/pause/resume.
- Kill switches: `/crm/settings` (disabling requires Soft Wall).

## Sender incident / policy block

1. Check `/crm/deliverability` and `/crm/ops` alerts.
2. Confirm suppressions at `/crm/suppressions`.
3. Pause workflows and campaigns before changing sender readiness.

## Stale dashboard

Ops and analytics show last-updated / freshness timestamps. If polling fails, the UI labels degraded/incomplete state instead of faking live motion.

## Support bundle

From the node inspector, create a redacted support bundle (`POST /api/crm/visual/support-bundle`). Secrets stay redacted.

## Rollback

Edit creates a new draft version. Re-publish a known-good graph after Soft Wall review. Do not mutate immutable published snapshots in place.
