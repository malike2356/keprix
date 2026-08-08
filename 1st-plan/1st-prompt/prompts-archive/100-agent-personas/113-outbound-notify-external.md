# keprix - Prompt 113: Outbound Notify External

## Context

Read `34-notifications-inbox-alert-routing-and-escalations.md` and `86-external-human-review-gateway.md`.

Prompt 24 covers the internal notification system: workspace inbox, mobile push, internal alerts, and in-app delivery. That system routes notifications to keprix users and to channels (Slack, Telegram, WhatsApp, etc.) that the operator controls.

This prompt covers a different scenario: dispatching a notification to an **external party** who is not a keprix user, has no channel configured in the system, and must be reached at an address the caller specifies at the time of dispatch. The content is typically a structured, transactional message (a review request, a compliance alert, an expiry warning, an audit report), not a conversational message.

Use cases:

- Review gateway (Prompt 117) sends a sign-off request to a Clinical Safety Officer by email.
- Pack gate (Prompt 132) notifies an external compliance reviewer that a new software version is pending their approval.
- A playbook step sends an evidence pack to an external auditor.
- A compliance scan result is posted to a client organisation's incident webhook.
- A hazard log is emailed to a regulatory body.

The key differences from Prompt 24:
- Recipient is an arbitrary external email address or webhook URL, not a registered keprix user.
- No inbox: the message is sent outbound only; there is no reply handling or read-receipt polling.
- Delivery confirmation and bounce tracking are required for audit purposes.
- The SMTP sender identity must be configurable (operators may need to send from a specific domain).
- Webhook payloads are signed to allow recipients to verify authenticity.

---

## File Structure

```
keprix/backend/notify_external/
    __init__.py
    smtp_sender.py      - SMTP-based email dispatch (plain text + HTML)
    webhook_sender.py   - HTTP POST webhook dispatch with signature
    bounce_handler.py   - tracks delivery failures and bounces
    delivery_log.py     - append-only delivery log
    templates.py        - email template renderer (Jinja2-free; uses Python string formatting)
    routes.py           - API for send, status, and delivery log
    schemas.py          - Pydantic schemas

keprix/tests/notify_external/
    test_smtp_sender.py
    test_webhook_sender.py
    test_bounce_handler.py
    test_routes.py

keprix/ui/web/src/app/(workspace)/settings/notifications/external/
    page.tsx            - external notification settings: SMTP config, webhook defaults, delivery log
```

---

## Database

```sql
CREATE TABLE external_notification_config (
    workspace_id UUID PRIMARY KEY,
    smtp_host TEXT,
    smtp_port INTEGER DEFAULT 587,
    smtp_use_tls BOOLEAN NOT NULL DEFAULT TRUE,
    smtp_username TEXT,
    smtp_password_vault_id UUID,
    -- reference to vault item (Prompt 08) holding encrypted SMTP password
    smtp_from_email TEXT,
    smtp_from_name TEXT,
    webhook_signing_secret_vault_id UUID,
    -- HMAC secret for signing outbound webhook payloads; stored in vault
    max_retries INTEGER NOT NULL DEFAULT 3,
    retry_interval_seconds INTEGER NOT NULL DEFAULT 300,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE external_notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL,
    channel TEXT NOT NULL,
    -- 'email' or 'webhook'
    recipient_address TEXT NOT NULL,
    -- email address or webhook URL
    subject TEXT,
    -- for email only
    body_text TEXT,
    -- plain text body (email) or JSON payload stringified (webhook)
    body_html TEXT,
    -- HTML body for email (optional)
    template_name TEXT,
    -- name of template used, if any
    template_vars JSONB,
    -- template variables, for audit/replay
    status TEXT NOT NULL DEFAULT 'pending',
    -- 'pending', 'sent', 'failed', 'bounced', 'cancelled'
    attempts INTEGER NOT NULL DEFAULT 0,
    last_attempted_at TIMESTAMPTZ,
    delivered_at TIMESTAMPTZ,
    failure_reason TEXT,
    triggered_by TEXT,
    -- 'review_gateway', 'pack_gate', 'playbook', 'api', 'manual'
    triggered_by_id TEXT,
    -- ID of the triggering entity (review_request_id, gate_record_id, etc.)
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX ON external_notifications(workspace_id, status);
CREATE INDEX ON external_notifications(workspace_id, triggered_by, triggered_by_id);
CREATE INDEX ON external_notifications(status, last_attempted_at) WHERE status = 'pending';
```

---

## SMTP Sender (`smtp_sender.py`)

```python
async def send_email(
    workspace_id: str,
    to_email: str,
    to_name: str | None,
    subject: str,
    body_text: str,
    body_html: str | None = None,
    triggered_by: str = "api",
    triggered_by_id: str | None = None,
) -> str:
    """
    Sends an email to an external recipient.
    Returns the external_notification ID.
    """
```

Implementation:

1. Load SMTP config from `external_notification_config` for the workspace.
2. If no workspace SMTP config: fall back to system SMTP config from `keprix/config/smtp.yaml`. If neither is set, raise `SMTPNotConfigured` and log a warning.
3. Build `email.mime.multipart.MIMEMultipart('alternative')`. Set From, To, Subject, Date, Message-ID headers.
4. Attach plain text part. If `body_html` provided, attach HTML part.
5. Add header `X-keprix-Workspace: {workspace_id}` (helps with delivery log correlation).
6. Connect with `aiosmtplib.SMTP` using `tls` or `starttls` based on config.
7. Authenticate with username + password from vault.
8. Send and await response.
9. Record delivery in `external_notifications` with `status = 'sent'` and `delivered_at = NOW()`.
10. On `SMTPException`: record `status = 'failed'`, increment `attempts`, store `failure_reason`.
11. Never log SMTP password or body content in error logs. Log only: workspace_id, recipient_domain (not full address), subject, error code.

For the recipient, store only the full address in `external_notifications.recipient_address`. In all other log outputs (audit log, error log), log only the domain: `recipient_email.split('@')[1]`.

---

## Webhook Sender (`webhook_sender.py`)

```python
async def send_webhook(
    workspace_id: str,
    webhook_url: str,
    payload: dict,
    triggered_by: str = "api",
    triggered_by_id: str | None = None,
    timeout_seconds: int = 30,
) -> str:
    """
    POSTs a signed JSON payload to an external webhook URL.
    Returns the external_notification ID.
    """
```

Implementation:

1. Load `webhook_signing_secret_vault_id` from `external_notification_config`.
2. Serialise `payload` to canonical JSON (`separators=(',', ':')`, keys sorted).
3. Compute `X-keprix-Signature: sha256={hmac_sha256(payload_bytes, secret)}`.
4. Add headers: `Content-Type: application/json`, `X-keprix-Signature`, `X-keprix-Workspace: {workspace_id}`, `X-keprix-Delivery-ID: {notification_id}`, `User-Agent: keprix/{version}`.
5. POST with `httpx.AsyncClient` using the configured timeout.
6. Success: HTTP 2xx. Record `status = 'sent'`.
7. Failure: non-2xx or timeout. Record `status = 'failed'`, store response code and first 500 chars of response body as `failure_reason`.
8. Never follow redirects (security: prevents SSRF via redirect chain to internal addresses).
9. Validate `webhook_url` before dispatch: must be `https://`. Reject `http://`, `localhost`, `127.`, `10.`, `192.168.`, `169.254.` prefixes with `WebhookTargetRejected` error.

---

## Retry Logic

A cron job (Prompt 15) runs every 5 minutes and retries failed pending notifications:

```python
async def retry_failed_external_notifications():
    due = await db.fetchall(
        """SELECT * FROM external_notifications
           WHERE status = 'pending'
           AND attempts < max_retries_for_workspace(workspace_id)
           AND (last_attempted_at IS NULL OR last_attempted_at < NOW() - INTERVAL '5 minutes')
           ORDER BY created_at ASC
           LIMIT 100"""
    )
    for n in due:
        if n.channel == "email":
            await smtp_sender.resend(n)
        elif n.channel == "webhook":
            await webhook_sender.resend(n)
```

After `max_retries` attempts with no success:
- Set `status = 'failed'` permanently.
- Send a workspace inbox notification (Prompt 24): "Failed to deliver external notification to {recipient_domain} after {attempts} attempts. Subject: {subject}."
- Log to audit log.

---

## Email Templates

Store templates as Python string constants in `templates.py`. No Jinja2 dependency. Use `str.format_map()` with a safedict that returns `[missing]` for unknown keys.

Provide these built-in templates:

```python
TEMPLATES = {
    "review_request": {
        "subject": "[Action needed] {title} - review required by {expires_date}",
        "text": """
You have been asked to review: {title}

{context_message}

Review and decide here:
{review_url}

This link expires: {expires_at}
Sent by: {workspace_name}
""",
        "html": """<p>You have been asked to review: <strong>{title}</strong></p>
<p>{context_message}</p>
<p><a href="{review_url}" style="...">Review and decide</a></p>
<p>This link expires: {expires_at}</p>
<p>Sent by: {workspace_name}</p>""",
    },

    "review_reminder": {
        "subject": "[Reminder] {title} - review still pending",
        "text": "...",
        "html": "...",
    },

    "review_receipt": {
        "subject": "Your decision has been recorded: {title}",
        "text": """
Your decision for '{title}' has been recorded.

Decision: {action}
Recorded at: {decided_at}
Reference: {review_request_id}

You can close this email.
""",
        "html": "...",
    },

    "pack_gate_pending": {
        "subject": "[Approval needed] {pack_name} v{version} is awaiting your sign-off",
        "text": "...",
        "html": "...",
    },

    "evidence_pack_ready": {
        "subject": "Evidence pack ready: {date_from} to {date_to}",
        "text": "...",
        "html": "...",
    },
}
```

Operators can add custom templates via the API. Custom template bodies are sanitised: only the variables `{key}` form is allowed; `<script>` and other dangerous HTML tags are stripped before storage.

---

## API Endpoints

```
POST /api/notify-external/send
     Requires workspace auth.
     Body: {
       channel: 'email' | 'webhook',
       recipient_address: string,
       subject?: string,               -- email only
       body_text?: string,             -- raw text; use instead of template
       body_html?: string,
       template_name?: string,
       template_vars?: object,
       triggered_by?: string,
       triggered_by_id?: string
     }
     Returns: { notification_id, status: 'pending' }

GET  /api/notify-external/notifications
     Query: status, channel, triggered_by, page
     Returns: paginated delivery log (no body content; metadata only)

GET  /api/notify-external/notifications/{id}
     Returns: full notification record (body_text omitted for security; shows status and metadata)

POST /api/notify-external/notifications/{id}/retry
     Manually triggers a retry for a failed notification.

GET  /api/notify-external/config
     Returns: SMTP and webhook config (password and secrets replaced with 'configured' or 'not set')

PUT  /api/notify-external/config
     Body: { smtp_host, smtp_port, smtp_use_tls, smtp_username, smtp_password,
             smtp_from_email, smtp_from_name }
     Password is stored in vault; not echoed back.

POST /api/notify-external/test-email
     Body: { to_email }
     Sends a test email from the workspace SMTP config to verify it is working.
     Returns: { notification_id, status }

GET  /api/notify-external/templates
     Returns: list of built-in and custom templates (names and variable list; no body)

POST /api/notify-external/templates
     Body: { name, subject_template, text_template, html_template? }
     Creates a custom template.
```

---

## Settings UI (`/settings/notifications/external`)

Sections:

**SMTP Configuration**: Form for host, port, TLS toggle, username, password (write-only field), from email and name. "Test email" button sends to the current user's email.

**Webhook Signing**: Shows whether a signing secret is configured. "Regenerate secret" button (invalidates old secret; warns that existing webhook recipients will need the new public key).

**Delivery Log**: Table of recent outbound notifications. Columns: sent at, channel, recipient domain, subject/event type, status, attempts. Click to see detail (no body content).

**Templates**: List of available templates with variable names. Link to API docs for custom template creation.

---

## Security Requirements

- Webhook target URL must be `https://`. Reject all other schemes.
- SSRF prevention: reject webhook URLs that resolve to private IP ranges. Check both hostname and any DNS-resolved IP.
- SMTP password is stored in vault only. Never returned by any API endpoint.
- `body_text` and `body_html` are not stored in the audit log; only metadata (template name, triggered_by, status) is logged.
- Recipient full email address is stored only in `external_notifications`. Audit log and error logs store only the domain.
- Rate limit: maximum 100 external notifications per workspace per hour. Return HTTP 429 with `Retry-After` header if exceeded. (This prevents abuse if a playbook loop dispatches unbounded emails.)
- Custom templates are sanitised before storage: strip `<script>`, `<iframe>`, `<object>`, `<embed>`, event attributes (`onclick`, `onload`, etc.).

---

## Integration Points

Callers should use the Python API, not the HTTP API, for internal dispatch:

```python
from keprix.backend.notify_external import smtp_sender, webhook_sender

# In review_gateway/dispatch.py:
await smtp_sender.send_email(
    workspace_id=workspace_id,
    to_email=review_request.reviewer_email,
    to_name=review_request.reviewer_name,
    subject=None,          # use template
    body_text=None,
    template_name="review_request",
    template_vars={
        "title": review_request.title,
        "context_message": review_request.context_message,
        "review_url": review_url,
        "expires_at": review_request.expires_at.strftime("%d %b %Y %H:%M UTC"),
        "expires_date": review_request.expires_at.strftime("%d %b %Y"),
        "workspace_name": workspace.name,
    },
    triggered_by="review_gateway",
    triggered_by_id=str(review_request.id),
)
```

---

## Acceptance Criteria

- `POST /api/notify-external/send` with `channel: 'email'` and a valid SMTP config delivers an email and records `status = 'sent'`.
- `POST /api/notify-external/test-email` sends a test email and returns the notification ID.
- A webhook dispatch includes `X-keprix-Signature` and the signature verifies against the payload.
- A webhook dispatch to `http://` (not HTTPS) is rejected with HTTP 422 before any network call is made.
- A webhook dispatch to `http://localhost` is rejected with HTTP 422 (SSRF guard).
- A failed email notification retries up to `max_retries` times. After final failure, workspace inbox receives an alert.
- SMTP password is never returned by `GET /api/notify-external/config`.
- Recipient full email is not present in the audit log; only the domain is.
- `GET /api/notify-external/notifications/{id}` does not include the body text in its response.
- Dispatching 101 emails in one hour from the same workspace returns HTTP 429 on the 101st.
- A template with `<script>` in the HTML body is rejected on POST `/api/notify-external/templates`.
- Review gateway (Prompt 117) uses `smtp_sender.send_email` with the `review_request` template for new review requests and `review_receipt` for decision receipts.
