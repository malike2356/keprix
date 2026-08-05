# Email

Keprix provides an IMAP/SMTP email workspace for inbox triage, AI summaries, compose/send, and interval auto-sync with Gmail and other providers. It is separate from **external notification SMTP** used for system alerts.

## Web UI (`/email`)

| Area | Purpose |
| --- | --- |
| Connect email | Add Gmail (app password), Outlook, Yahoo, or generic IMAP/SMTP |
| Interval | Per-account resync interval (1m to 1h; default 5m) |
| Compose | Send mail from Keprix via the connected SMTP account |
| Inbox | Synced messages; star, open, priority chips |
| Detail | Body, Summarize, AI reply draft, Reply |

**Sync now** pulls immediately. The background poller also resyncs each active account when its interval is due (tick ~30s).

## Connect Gmail

Preferred without OAuth client setup:

1. Google Account → Security → App passwords (2FA required)
2. `/email` → **Connect email** → **Gmail (app password)**
3. Paste Gmail address + app password
4. Set resync interval and Connect

Optional OAuth: if `GOOGLE_OAUTH_CLIENT_ID` / secret / redirect are configured, the UI shows **Connect Gmail with Google OAuth** (IMAP/SMTP XOAUTH2).

## Auto-sync intervals

Each account stores `poll_interval_seconds` (minimum 30). The poller only fetches when `last_polled_at` is older than that interval.

## Compose and send

Use **Compose** on `/email`, or:

```bash
curl -X POST http://localhost:3334/api/email/send \
  -H "Content-Type: application/json" \
  -d '{
    "to_addresses": ["peer@example.com"],
    "subject": "Hello from Keprix",
    "body": "Sent via SMTP"
  }'
```

## API highlights

- `GET /api/email/providers`
- `POST/GET/PUT/DELETE /api/email/accounts`
- `POST /api/email/accounts/{id}/test`
- `POST /api/email/sync`
- `GET /api/email/inbox`
- `POST /api/email/send`

On startup, Keprix ensures `email_accounts`, `emails`, `email_drafts`, and `vault_items` exist (`checkfirst` create).

## Related

- [Calendar](calendar.md) (similar interval sync pattern)
- [Workspace overview](workspace.md)
