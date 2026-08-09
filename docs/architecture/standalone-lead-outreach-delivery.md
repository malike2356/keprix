# Standalone lead outreach delivery (Prompt 625)

**Status:** IMPLEMENTED (honest defaults)  
**Date:** 2026-08-09  
**Depends on:** Prompt 624 durable scheduler + Soft Wall park

## Purpose

Send Soft Wall **approved** campaign email through a configured provider, store provider IDs, and normalize ESP delivery events. Dry-run and not_configured stay honest (no fake live success).

## Default safety

| Env | Default | Meaning |
| --- | --- | --- |
| `KEPRIX_OUTREACH_DRY_RUN` | `1` | Approve / live path returns `dry_run=True`; Contabo/prod should keep this until SMTP/ESP is bound and intentionally enabled |
| `KEPRIX_OUTREACH_SOFT_WALL` | `1` | Cold sends park at Soft Wall before delivery |

Set `KEPRIX_OUTREACH_DRY_RUN=0` only when an SMTP `email_accounts` bind or ESP credentials are present.

## Sender resolution

Order in `outreach/delivery.py` `resolve_sender`:

1. Campaign `email_account_id` or control `default_email_account_id` → SMTP via `email_accounts` / vault
2. ESP when credentials present: SendGrid (`SENDGRID_API_KEY`), Mailgun (`MAILGUN_API_KEY` + `MAILGUN_DOMAIN`), SES (`AWS_ACCESS_KEY_ID` + `AWS_SECRET_ACCESS_KEY` + region; requires boto3)
3. Else `not_configured` (no `sent_at`, Soft Wall stays parked)

CE users bind their own mailbox credentials; there is no paid-plan gate.

## Soft Wall approve behaviour

- Revalidate suppression / pause / consent before send
- `not_configured`: leave `awaiting_approval`, do not advance `current_step`, do not stamp `sent_at`
- Explicit dry-run or env dry-run success: stamp `provider=dry_run` + `provider_message_id` + `sent_at`
- Live SMTP/ESP success: stamp provider fields + `delivery_state` (`sent` / `accepted`)

## Provider events

- Routes: `POST /api/outreach/webhooks/{provider}` (public; signature when verify key set)
- Internal: `POST /api/outreach/provider-events/apply`
- Normalizers: SES SNS, SendGrid, Mailgun → contract types (`delivered`, `hard_bounce`, `complaint`, …)
- Replay: `outreach_provider_events` unique `(workspace_id, idempotency_key)`
- Hard bounce / complaint / unsubscribe → CRM suppression + stop enrollments
- Open / click applied only when control settings `allow_open_tracking` / `allow_click_tracking` (default off; labelled optional in UI)

## Reconciliation

`reconcile_delivery` flags `sent`/`accepted` messages older than N minutes without delivered/bounce (`delivery_drift` in `send_error`). Does not auto-resend. Health: `GET /api/outreach/delivery/health` (also folded into scheduler health). Daily cron seed: `outreach-delivery-reconcile`.

## Delivery state machine

Monotonic forward ranks for normal progress. Terminal failure / complaint / unsubscribe may override a prior `delivered` (late bounce policy). Documented in `delivery.next_delivery_state`.

## Honesty matrix notes

| Capability | Class |
| --- | --- |
| Live email send | REAL when SMTP bind works and dry-run off; PARTIAL under default dry-run |
| Provider events | REAL for normalizer + apply (fixtures); ESP live send BLOCKED_OPTIONAL_CREDENTIALS without keys |

`standalone_outreach_ready` is true after series Prompt 628.

## APIs

- `POST /api/outreach/messages/preview` (template + lead_id)
- Approve / reject / modify / expire Soft Wall paths under `/api/outreach/approvals/*`
- `GET /api/outreach/delivery/health`, `POST /api/outreach/delivery/reconcile`
