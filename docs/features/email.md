# Email

Keprix provides an IMAP/SMTP email workspace for inbox triage, AI summaries, and programmatic send. It is separate from **external notification SMTP** used for system alerts.

## Web UI (`/email`)

Three-column inbox:

| Column | Purpose |
| --- | --- |
| Accounts | Connected IMAP/SMTP mailboxes |
| Inbox | Synced messages; star, open, priority chips |
| Detail | Body, **Summarize**, **AI reply draft** |

**Sync** pulls new mail via IMAP (`POST /api/email/sync`).

### What the UI does today

- Read and triage synced messages
- Mark read, toggle star
- Generate AI summary and priority tags
- Create AI reply **draft** on the server

### What the UI does not do yet

- Compose new mail
- Edit or send reply drafts from the browser

Sending is available via API and agent tools (see below).

## Connect an account

Accounts use IMAP (inbound) and SMTP (outbound). Add via API:

```bash
curl -X POST http://localhost:3333/api/email/accounts \
  -H "Content-Type: application/json" \
  -d '{
    "label": "Work",
    "email_address": "you@example.com",
    "imap_host": "imap.example.com",
    "imap_port": 993,
    "smtp_host": "smtp.example.com",
    "smtp_port": 587,
    "username": "you@example.com",
    "password": "your-app-password",
    "use_tls": true
  }'
```

### OAuth (Gmail / Outlook)

When OAuth env vars are set:

- `GET /api/email/accounts/gmail/auth` returns Google consent URL
- `GET /api/email/accounts/microsoft/auth` returns Microsoft consent URL

Callbacks create accounts with tokens stored in the vault.

### Test connection

```bash
curl -X POST http://localhost:3333/api/email/accounts/{account_id}/test
```

## Send mail

Direct send (requires a configured account):

```bash
curl -X POST http://localhost:3333/api/email/send \
  -H "Content-Type: application/json" \
  -d '{
    "to_addresses": ["recipient@example.com"],
    "subject": "Hello from Keprix",
    "body": "Plain text body"
  }'
```

Draft workflow:

1. `POST /api/email/{email_id}/reply` or `/ai-reply-draft`
2. Edit via `PUT /api/email/drafts/{draft_id}`
3. `POST /api/email/drafts/{draft_id}/send`

## AI pipeline

| Endpoint | Action |
| --- | --- |
| `POST /api/email/{id}/ai-summary` | Summary, tags, priority |
| `POST /api/email/{id}/ai-reply-draft` | LLM-generated reply body |

Uses the instance default LLM provider.

## Agent and MCP tools

The email MCP server exposes `list_emails`, `send_email`, and related tools for agent automation.

## External notification SMTP (different)

`/settings/notifications/external` configures SMTP for **system** emails (reviewers, compliance). That does not populate the `/email` inbox.

## Environment variables (legacy / fallback)

```bash
KEPRIX_SMTP_HOST=
KEPRIX_SMTP_PORT=587
KEPRIX_SMTP_USER=
KEPRIX_SMTP_PASS=
KEPRIX_EMAIL_FROM=
KEPRIX_RESEND_API_KEY=
```

Prefer per-account IMAP/SMTP configuration for the workspace inbox.

## Related

- [Contacts](contacts.md)
- [Notifications](notifications.md)
- [API reference](../reference/api.md)
