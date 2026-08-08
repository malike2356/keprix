# keprix - Prompt 11: Email Integration

## Context

Sources:
- `odysseus/routes/email_routes.py`, `email_helpers.py`, `email_pollers.py`
- `odysseus/mcp_servers/email_server.py`
- `odysseus/docs/email-outlook.md`
- `hermes-agent/optional-skills/email/`
- `hermes-agent/skills/email/`
Output: `keprix/backend/email/`

## Overview

keprix includes a full IMAP/SMTP email client built into the agent workspace.
The agent can read, triage, summarize, tag, draft, and send email autonomously.
Users can also view their inbox directly from the keprix web UI.

## Files to Port

```
odysseus/routes/email_routes.py   -> backend/email/routes.py
odysseus/routes/email_helpers.py  -> backend/email/helpers.py
odysseus/routes/email_pollers.py  -> backend/email/pollers.py
odysseus/mcp_servers/email_server.py -> backend/email/mcp_server.py
```

Port Hermes email skills:
```
hermes-agent/skills/email/        -> backend/skills/packs/email/   (already in Prompt 07)
hermes-agent/optional-skills/email/ -> backend/skills/optional/email/
```

## Database Schema

`backend/email/migrations/001_email_schema.sql`:
```sql
CREATE TABLE email_accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    label TEXT NOT NULL DEFAULT 'Default',
    email_address TEXT NOT NULL,
    imap_host TEXT NOT NULL,
    imap_port INT NOT NULL DEFAULT 993,
    smtp_host TEXT NOT NULL,
    smtp_port INT NOT NULL DEFAULT 587,
    username TEXT NOT NULL,
    password_encrypted TEXT NOT NULL,  -- AES-256 encrypted in vault
    use_tls BOOLEAN DEFAULT true,
    use_starttls BOOLEAN DEFAULT false,
    poll_interval_seconds INT DEFAULT 60,
    last_polled_at TIMESTAMPTZ,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE emails (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id UUID REFERENCES email_accounts(id) ON DELETE CASCADE,
    user_id TEXT NOT NULL,
    message_id TEXT NOT NULL,         -- IMAP Message-ID header
    uid BIGINT,                        -- IMAP UID
    folder TEXT NOT NULL DEFAULT 'INBOX',
    from_address TEXT NOT NULL,
    from_name TEXT,
    to_addresses TEXT[] NOT NULL,
    cc_addresses TEXT[] DEFAULT '{}',
    subject TEXT NOT NULL DEFAULT '',
    body_text TEXT,
    body_html TEXT,
    preview TEXT,                      -- first 200 chars of body_text
    has_attachments BOOLEAN DEFAULT false,
    is_read BOOLEAN DEFAULT false,
    is_starred BOOLEAN DEFAULT false,
    is_trashed BOOLEAN DEFAULT false,
    ai_summary TEXT,
    ai_tags TEXT[] DEFAULT '{}',
    ai_priority TEXT DEFAULT 'normal',
    received_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(account_id, uid, folder)
);

CREATE INDEX ON emails (user_id, is_read, received_at DESC);
CREATE INDEX ON emails (user_id, is_starred);
CREATE INDEX ON emails USING gin(to_tsvector('english', subject || ' ' || coalesce(body_text, '')));
CREATE INDEX ON emails USING gin(ai_tags);

CREATE TABLE email_drafts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    account_id UUID REFERENCES email_accounts(id),
    reply_to_email_id UUID REFERENCES emails(id),
    to_addresses TEXT[] NOT NULL DEFAULT '{}',
    cc_addresses TEXT[] DEFAULT '{}',
    subject TEXT DEFAULT '',
    body TEXT DEFAULT '',
    is_ai_generated BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

## API Endpoints

```
POST   /api/email/accounts               - add email account
GET    /api/email/accounts               - list accounts
PUT    /api/email/accounts/{id}          - update account settings
DELETE /api/email/accounts/{id}          - remove account
POST   /api/email/accounts/{id}/test     - test IMAP/SMTP connection

GET    /api/email/inbox                  - list emails (paginated, filters: read/unread/starred/tag)
GET    /api/email/{id}                   - get email with full body
PUT    /api/email/{id}/read              - mark read
PUT    /api/email/{id}/star              - toggle star
DELETE /api/email/{id}                   - move to trash
POST   /api/email/{id}/reply             - create reply draft
POST   /api/email/{id}/forward           - create forward draft
POST   /api/email/{id}/ai-summary        - force AI summary of this email
POST   /api/email/{id}/ai-reply-draft    - generate AI reply draft
GET    /api/email/search?q=              - full-text + AI tag search

POST   /api/email/drafts                 - create draft
GET    /api/email/drafts                 - list drafts
PUT    /api/email/drafts/{id}            - update draft
DELETE /api/email/drafts/{id}            - delete draft
POST   /api/email/drafts/{id}/send       - send draft

POST   /api/email/send                   - send email directly (no draft step)
POST   /api/email/sync                   - trigger immediate IMAP sync
GET    /api/email/sync/status            - last sync time per account
```

## IMAP Poller

`backend/email/pollers.py`:
- Runs as a background asyncio task within the main backend process
- Polls each active account at its configured `poll_interval_seconds`
- On new emails: fetch headers + body, store in `emails` table, trigger AI pipeline
- Uses `imaplib` or `aioimaplib` for async IMAP
- Idle mode (IMAP IDLE command) when server supports it for push-like behavior
- Port `odysseus/routes/email_pollers.py` logic verbatim; adapt DB layer

## AI Email Pipeline

When a new email arrives, automatically:
1. Generate a 2-sentence `ai_summary` (use cheapest configured provider)
2. Assign `ai_tags` (up to 5 keywords: e.g. ["invoice", "urgent", "client"])
3. Assign `ai_priority`: "urgent", "normal", or "low" based on content
4. If priority is "urgent", optionally notify via configured messaging channel

This pipeline runs in a background queue (asyncio Task). It must not block
the IMAP poller.

## AI Reply Draft

`POST /api/email/{id}/ai-reply-draft` generates a full reply body:
- Reads the original email thread context (last 5 messages if threaded)
- Uses the user's name and email signature from `workspace/profile`
- Generates a reply matching the tone and formality of the original
- Saves as a draft (is_ai_generated=true)
- Does not send automatically; user must review and click Send

## Outlook / Exchange Support

From `odysseus/docs/email-outlook.md`, implement OAuth2 support for:
- Microsoft 365 / Outlook (Microsoft Graph API)
- Configure via: `MICROSOFT_CLIENT_ID`, `MICROSOFT_CLIENT_SECRET`, `MICROSOFT_TENANT_ID`
- `POST /api/email/accounts/microsoft/auth` - start OAuth flow
- `GET /api/email/accounts/microsoft/callback` - OAuth callback
- Once authenticated, Microsoft 365 accounts appear alongside IMAP accounts

## Email MCP Server

Port `odysseus/mcp_servers/email_server.py` to `backend/email/mcp_server.py`.
This exposes email capabilities as MCP tools so the agent can:
- `list_emails(folder, limit, unread_only)`
- `read_email(id)`
- `send_email(to, subject, body)`
- `create_draft(to, subject, body)`
- `mark_read(id)`
- `search_emails(query)`

## Email Skill Integration

The email skills in `backend/skills/packs/email/` give the agent natural
language email capabilities:
- "Check my email" - fetches and summarizes recent unread emails
- "Reply to [sender]'s email about [subject]" - draft + send flow
- "Mark all emails from [domain] as read"
- "Find emails about [topic]"
- "Schedule a reminder to reply to [email]" - creates a task

## Gmail Support

Implement Gmail via IMAP (app passwords) as the default documented path.
For OAuth2 Gmail: `POST /api/email/accounts/gmail/auth`. Use `google-auth` package.

## Acceptance Criteria

- `POST /api/email/accounts` with valid IMAP/SMTP credentials returns 201
- `POST /api/email/accounts/{id}/test` connects and returns folder list
- Poller fetches new emails into `emails` table within 2x poll interval
- `GET /api/email/inbox?unread=true` returns only unread emails
- `POST /api/email/{id}/ai-summary` returns a non-empty string summary
- `POST /api/email/send` sends a real email when SMTP is configured
- Email MCP server starts and responds to `list_tools()` with at least 6 tools
