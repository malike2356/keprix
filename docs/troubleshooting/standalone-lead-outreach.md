# Troubleshooting: Standalone lead and outreach

Symptom → cause → fix for Community Edition, Docker, hosted Postgres, providers, imports, Soft Wall, scheduler, replies, and observability.

## CRM import fails or columns missing

- **Cause:** Wrong sheet shape or analytics extras missing for XLS/ODS.
- **Fix:** Use the 17-column synthetic shape; install `keprix[analytics]` for XLS/ODS; check `/api/crm/leads/ingest-preview`.

## Soft Wall backlog grows

- **Cause:** `require_approval` campaigns with no human approve.
- **Fix:** Review `/outreach` approvals; `GET /api/outreach/observability` → `approval_backlog`.

## Sends stay dry-run or not_configured

- **Cause:** `KEPRIX_OUTREACH_DRY_RUN=1` or no bound SMTP/ESP account.
- **Fix:** For local proof only, set dry-run `0` and bind SMTP (Mailpit overlay) or ESP keys. Contabo stays dry-run unless owner flips.

## Provider events not updating delivery state

- **Cause:** Unsigned webhooks rejected, or provider_message_id mismatch.
- **Fix:** Configure signing keys; apply via `/api/outreach/provider-events/apply` with matching ids; check `provider_event_lag_seconds`.

## Replies unmatched

- **Cause:** Missing In-Reply-To / References / thread id, or cross-workspace.
- **Fix:** Confirm outbound stored `provider_message_id`; scan with `outreach_scan_replies`; review `unmatched_replies` on observability.

## Scheduler idle / due age rising

- **Cause:** Cron not seeded, worker lease stuck, business hours gate.
- **Fix:** Seed outreach crons; call process-due; inspect `queue_depth`, `oldest_due_age_seconds`, `dead_letters`.

## Hosted isolation surprise

- **Cause:** Missing `X-Workspace-Id` or wrong workspace scope.
- **Fix:** Always pass workspace; isolation tests under `tests/crm/test_crm_durable_storage.py` and `tests/outreach/test_outreach_workspace_isolation.py`.

## Database latency / migrate drift

- **Cause:** Schema behind Alembic or dual-backend mismatch.
- **Fix:** `keprix crm-migrate`; observability `database_latency_ms`; see `standalone-lead-outreach-durable-storage.md`.

## Backup restore broken Soft Wall

- **Cause:** Ops SQLite/Postgres out of sync with outreach messages.
- **Fix:** Restore CRM + outreach + ops together; reconcile delivery; re-check approvals.

Related: [standalone-lead-outreach-ops.md](../architecture/standalone-lead-outreach-ops.md), [soft-wall-and-outreach.md](soft-wall-and-outreach.md), [agentic-crm.md](agentic-crm.md).
