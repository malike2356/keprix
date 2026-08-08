# Agent brief: Prompt 113 outbound notify external

**Status:** Archived in `prompts-archive/113-outbound-notify-external.md`  
**Verification closed:** 2026-07-12 (automated gaps closed; smoke tests green).
**Reconciled:** 2026-07-05 (checklist vs code/tests)  
**Working directory:** `/opt/lampp/htdocs/verlox/keprix/`  
**Goal:** Ship real outbound email and signed webhook dispatch to arbitrary external recipients, with delivery logging, retries, and audit-safe metadata. Replace jsonl email stubs used today by pack gate and review gateway.

**MVP:** Shipped. Module, settings UI, pack gate + review gateway integration, 7 tests in `tests/notify_external/test_routes.py`.

**Blocks:** Prompt 112 (pack gate approver email), Prompt 111 (`evidence_pack_ready` template), archived Prompt 107 (review gateway SMTP).

---

## Context

Prompt 24 (notifications inbox) is still pending. That is fine: this prompt is intentionally narrower. It sends one-way transactional messages to external parties (CSO email, auditor webhook, regulatory contact) without inbox or reply handling.

**Implemented:** `src/keprix/notify_external/` with SMTP + webhook senders, delivery store, templates, settings UI, and callers updated in `pack_gate/notifications.py` and `review_gateway/dispatch.py`.

Reuse patterns from:

- `src/keprix/email/helpers.py` (`send_smtp_message`, connection testing)
- `src/keprix/security/vault_service.py` (SMTP password storage; Prompt 08)
- `src/keprix/scout/signing.py` (HMAC signing pattern for webhooks)

---

## File layout (create)

```text
src/keprix/notify_external/
  __init__.py          # export send_email, send_webhook
  schemas.py           # Pydantic request/response models
  store.py             # config + notification records (JSONL or DB; match pack_gate store style)
  smtp_sender.py       # async SMTP dispatch
  webhook_sender.py    # signed HTTPS POST
  templates.py         # built-in templates (str.format_map, no Jinja2)
  bounce_handler.py    # failure classification helpers
  routes.py            # /api/notify-external/*

tests/notify_external/
  test_smtp_sender.py
  test_webhook_sender.py
  test_bounce_handler.py
  test_routes.py

frontend/src/app/(workspace)/settings/notifications/external/page.tsx
frontend/src/lib/notify-external-api.ts
```

Wire router in `src/keprix/api/server.py`.

---

## Implementation checklist

### Core senders

| Task | Detail |
| --- | --- |
| SMTP config | Per-workspace `external_notification_config`; password in vault; fallback to system `config/smtp.yaml` if unset |
| `send_email()` | `aiosmtplib` or reuse `email.helpers`; `MIMEMultipart('alternative')`; `X-Keprix-Workspace` header |
| Webhook guard | HTTPS only; reject `localhost`, RFC1918, link-local; no redirect follow; 30s timeout |
| Signature | `X-Keprix-Signature: sha256={hmac}` on canonical JSON (sorted keys) |
| Delivery log | `external_notifications` table or JSONL store: status, attempts, `triggered_by`, `triggered_by_id` |
| Privacy | Full recipient only in notification row; audit/error logs use domain only |
| Rate limit | 100 sends/workspace/hour; HTTP 429 with `Retry-After` |

### Templates (`templates.py`)

Ship built-in templates from the prompt:

- `review_request`, `review_reminder`, `review_receipt`
- `pack_gate_pending`
- `evidence_pack_ready`

Custom templates via API: strip `<script>`, `<iframe>`, event attributes; reject on POST if dangerous.

### API (`routes.py`)

Implement endpoints from the prompt:

- `POST /api/notify-external/send`
- `GET /api/notify-external/notifications` (metadata only; no body)
- `GET /api/notify-external/notifications/{id}`
- `POST /api/notify-external/notifications/{id}/retry`
- `GET|PUT /api/notify-external/config`
- `POST /api/notify-external/test-email`
- `GET|POST /api/notify-external/templates`

### Retry job

Add cron entry (see `src/keprix/cron/`) every 5 minutes:

- Retry `pending` rows under `max_retries`
- On final failure: workspace inbox jsonl alert (same pattern as `pack_gate/notifications.py` until Prompt 24 ships)

### Settings UI

`frontend/src/app/(workspace)/settings/notifications/external/page.tsx`:

- SMTP form (write-only password field)
- Test email button
- Webhook signing secret status + regenerate
- Delivery log table (domain, status, attempts; no body)

Link from `settings/page.tsx`.

---

## Integration (required before archiving)

Refactor callers to use Python API, not HTTP:

```python
from keprix.notify_external.smtp_sender import send_email

# review_gateway/dispatch.py
await send_email(..., template_name="review_request", triggered_by="review_gateway", ...)

# pack_gate/notifications.py
await send_email(..., template_name="pack_gate_pending", triggered_by="pack_gate", ...)
```

Remove or gate the jsonl-only code paths behind a `KEPRIX_NOTIFY_EXTERNAL_STUB=1` test flag if needed for offline tests.

---

## Verification commands

```bash
cd /opt/lampp/htdocs/verlox/keprix

PYTHONPATH=src .venv/bin/python -m pytest tests/notify_external/ -q

# SSRF and scheme guards
PYTHONPATH=src .venv/bin/python -m pytest tests/notify_external/test_webhook_sender.py -q -k "reject"

# After integration
PYTHONPATH=src .venv/bin/python -m pytest tests/pack_gate/ tests/review_gateway/ -q

cd frontend && pnpm build
```

Manual: configure SMTP in UI, run test email, confirm row in delivery log with `status=sent`.

---

## Acceptance checklist (from Prompt 113)

- [x] `POST /api/notify-external/send` with valid SMTP delivers email; records `status=sent` (mocked SMTP in `test_send_email_records_sent_with_mocked_smtp`)
- [x] `POST /api/notify-external/test-email` returns notification ID (`test_test_email_returns_notification_id`)
- [x] Webhook includes verifiable `X-Keprix-Signature` (`test_webhook_signature_roundtrip`)
- [x] `http://` and `http://localhost` targets return HTTP 422 before network call (`test_reject_http_webhook`, `test_reject_localhost_webhook`, `test_send_webhook_rejects_http`)
- [x] Failed sends retry up to `max_retries`; final failure alerts workspace inbox (`notify_external/retry.py`, cron `job_type=notify_external_retry`, `POST .../retry`, `POST .../retry-pending`)
- [x] `GET /api/notify-external/config` never returns SMTP password (`test_get_config_masks_password`)
- [x] Audit log contains recipient domain only, not full address (`recipient_domain()` in senders; not isolated in tests)
- [x] `GET .../notifications/{id}` omits body text (`_public_notification` strips body fields)
- [x] 101st send in one hour returns HTTP 429 (`test_rate_limit_returns_429`)
- [x] Template with `<script>` rejected on create (`test_template_script_rejected`)
- [x] Review gateway uses `send_email` with `review_request` / `review_receipt` templates (`review_gateway/dispatch.py`)
- [x] Pack gate uses `send_email` with `pack_gate_pending` template (`pack_gate/notifications.py`)

### Hardening closed (2026-07-12)

1. Retry helper + cron job type `notify_external_retry` + `POST /api/notify-external/notifications/{id}/retry` and `/retry-pending`.
2. Tests for test-email, rate limit 429, mocked SMTP `status=sent`, and retry.

---

## Out of scope

- Full Prompt 24 inbox, push, Slack/Telegram routing
- Prompt 111 clinical events and evidence packs (separate brief; only wire `evidence_pack_ready` template here)
- Inbound bounce webhook ingestion (log failures only for now)

---

## Archive when done

1. All acceptance items checked
2. `tests/notify_external/` green
3. Pack gate and review gateway no longer write email jsonl stubs in production path
4. Move prompt to `planning/prompts/prompts-archive/113-outbound-notify-external.md`
5. Update `pending-prompts/PROMPT-IMPLEMENTATION-AUDIT.md`
