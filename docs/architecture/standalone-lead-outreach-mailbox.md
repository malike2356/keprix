# Standalone lead outreach: automatic mailbox reply scan (Prompt 626)

**Status:** REAL  
**Date:** 2026-08-09  
**Depends on:** Soft Wall send + provider events (625), email_accounts IMAP

## What is real

Inbound campaign replies are ingested automatically via:

1. **IMAP poll** of bound `email_accounts` (campaign `email_account_id` or control `default_email_account_id`) using `email.helpers.imap_session` / cursor-aware UID fetch.
2. **Normalized webhook / test path** via `POST /api/outreach/inbound/normalize` and `OutreachService.ingest_inbound_normalized`.

Shared normalizer: `src/keprix/outreach/inbound_mail.py`  
Workspace-scoped matcher: `src/keprix/outreach/thread_match.py`  
Service entrypoints: `scan_replies`, `ingest_inbound_normalized`

## Match order (never cross-workspace)

1. `provider_thread_id` on `outreach_messages`
2. `In-Reply-To` / `References` tokens vs `provider_message_id` (angle brackets stripped)
3. Correlation / reply token in subject or body (e.g. `[kp-xxxxx]`)
4. Mailbox + exact sender email + recent outbound (default 30 days)
5. Scored fallback → `match_status=ambiguous`, `review_status=needs_review` (no auto stage apply)

## Persistence

| Table / columns | Role |
| --- | --- |
| `outreach_inbound_cursors` | Durable IMAP UID and Gmail history cursors (`gmail_history` stored even when Gmail API is `BLOCKED_OPTIONAL_CREDENTIALS`) |
| `outreach_replies.provider_message_id` | Idempotency key with unique `(workspace_id, provider_message_id)` |
| `match_status` | `matched` \| `ambiguous` \| `unmatched` |
| `matched_message_id` | Linked outbound delivery |
| `review_status` | `needs_review` / `assigned` / `dismissed` / `applied` |
| `attachments_meta_json` | Filename / size / content_type only; unsafe types rejected |

Polling and webhook overlap are idempotent on `provider_message_id`.

## After a confident match

- `classify_and_apply_reply` runs (sequence stop/branch per policy).
- CRM Soft Wall engagement hook (`hook_soft_wall_reply`).
- Unsubscribe / not-interested create CRM suppressions immediately.
- Suggested `draft_response` is parked as Soft Wall approval with `kind=reply_draft` (never auto-sent).

Ambiguous and unmatched rows stay in the review queue (`GET /api/outreach/replies/review-queue`) until assign or dismiss.

## Operator APIs

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/api/outreach/scan-replies` | Poll bound mailboxes |
| POST | `/api/outreach/inbound/normalize` | Webhook / test ingest |
| GET | `/api/outreach/replies` | List (includes auto-ingested + match status) |
| GET | `/api/outreach/replies/review-queue` | Ambiguous / unmatched |
| POST | `/api/outreach/replies/{id}/assign` | Link to message/lead and classify |
| POST | `/api/outreach/replies/{id}/dismiss` | Close without apply |

Agent tool: `outreach_scan_replies` (cron seed calls this path for real).

## Contabo / dry-run

Keep `KEPRIX_OUTREACH_DRY_RUN=1` on Contabo for outbound. Mailbox scan still runs when accounts are bound; tests use mocked IMAP / injected messages and do not require live credentials.

## Out of scope (Prompt 627)

Do **not** use `sheet_preprocess` or `email_ingest` for campaign reply reconciliation. Channel-attachment import remains a separate capability.
