# keprix - Prompt 107: External Human Review Gateway

## Context

Read `superseded-03-core-agent-engine.md`,
`superseded-05-tools-and-terminal.md`,
`10-workspace-documents-notes-calendar.md`, and `24-notifications-inbox-alert-routing-and-escalations.md`
first. The agent spine and tools already live under `src/keprix/agent/` and `src/keprix/tools/`.

keprix's internal approval gates (Prompt 05 and 64) require the operator to confirm before a risky action runs. That pattern is for the person running keprix. This prompt builds a different, orthogonal mechanism: requesting a sign-off from an **external human** who is not a keprix user, has no login, and receives the request by email or webhook.

Use cases this covers:

- A Clinical Safety Officer who must digitally sign off on a Hazard Log before a software release proceeds (COMPASS).
- A legal reviewer who must approve a contract draft before an agent sends it.
- A compliance officer who must acknowledge a security scan report before a deployment continues.
- Any durable workflow that needs evidence of human review by a named external party.

The gateway is general-purpose. It does not know anything about COMPASS or clinical safety. Domain packs (Prompt 30) and playbooks (Prompt 51) compose on top of it.

---

## Core Concepts

**Review request:** A structured record created by keprix (or a playbook step) asking a named external reviewer to act on an artifact. Contains: artifact reference or inline content, reviewer identity (name, email, optionally webhook URL), action options (approve, reject, request-change), expiry time, and context message.

**Signed review token:** A time-limited HMAC-signed token embedded in the review URL. The reviewer clicks the link; the token authenticates the session without requiring a keprix account. Tokens must be single-use: once the reviewer submits a decision, the token is invalidated.

**Review page:** A lightweight unauthenticated web page served by keprix. Shows the artifact (rendered Markdown or PDF embed), the context message, and action buttons. No keprix workspace navigation. No sidebar. Responsive for mobile (reviewers often open email on phone).

**Decision record:** Once a reviewer acts, keprix stores the decision (approve/reject/request-change), the reviewer's name as supplied, the timestamp, the IP address (hashed, see Prompt 119), and the token ID. The decision record is immutable once created.

**Playbook integration:** A playbook step can `await review_request(artifact_id, reviewer_email, options)`. Execution pauses at that step. When the reviewer decides, the playbook resumes from the checkpoint with the decision in context.

---

## File Structure

```
keprix/backend/review_gateway/
    __init__.py
    models.py           - DB models for review requests and decisions
    tokens.py           - HMAC-signed token generation and validation
    dispatch.py         - outbound email and webhook dispatch
    routes.py           - API routes (create, status, public review page, submit decision)
    page_renderer.py    - renders the reviewer-facing HTML page
    schemas.py          - Pydantic schemas for request/response
    playbook_step.py    - ReviewRequestStep for use in durable playbooks (Prompt 51)

keprix/tests/review_gateway/
    test_tokens.py
    test_dispatch.py
    test_routes.py
    test_playbook_step.py

keprix/ui/web/src/app/(workspace)/review-gateway/
    page.tsx            - workspace view: list of open and closed review requests
    [id]/page.tsx       - detail view for a single review request (operator side)

keprix/ui/web/src/app/review/
    [token]/page.tsx    - public reviewer page (no auth required)
```

---

## Database

```sql
CREATE TABLE review_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL,
    title TEXT NOT NULL,
    context_message TEXT,
    artifact_type TEXT NOT NULL,
    -- 'markdown', 'pdf', 'json', 'url'
    artifact_content TEXT,
    -- inline content for markdown/json
    artifact_url TEXT,
    -- for pdf embed or external URL
    artifact_filename TEXT,
    reviewer_name TEXT NOT NULL,
    reviewer_email TEXT NOT NULL,
    reviewer_webhook_url TEXT,
    allowed_actions TEXT[] NOT NULL DEFAULT ARRAY['approve', 'reject'],
    -- e.g. ARRAY['approve', 'reject', 'request_change']
    token_id UUID NOT NULL UNIQUE,
    token_hash TEXT NOT NULL,
    -- HMAC-SHA256 of (token_id || workspace_id || expiry)
    expires_at TIMESTAMPTZ NOT NULL,
    reminder_at TIMESTAMPTZ,
    -- optional re-notify time if no decision by then
    status TEXT NOT NULL DEFAULT 'pending',
    -- 'pending', 'decided', 'expired', 'cancelled'
    playbook_run_id UUID,
    -- if triggered from a playbook, resume this run on decision
    playbook_step_id TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by_user_id UUID
);

CREATE TABLE review_decisions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    review_request_id UUID NOT NULL REFERENCES review_requests(id),
    action TEXT NOT NULL,
    -- 'approve', 'reject', 'request_change'
    reviewer_note TEXT,
    token_id UUID NOT NULL,
    reviewer_ip_hash TEXT,
    -- hashed per Prompt 119 GDPR rules
    decided_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (review_request_id)
    -- one decision per request; token invalidated on first submission
);

CREATE INDEX ON review_requests(workspace_id, status);
CREATE INDEX ON review_requests(token_id);
CREATE INDEX ON review_requests(expires_at) WHERE status = 'pending';
```

---

## Token Scheme

Tokens are generated as follows:

```python
import hmac, hashlib, secrets, base64

def generate_review_token(review_request_id: str, workspace_id: str, expires_at: datetime, secret_key: bytes) -> tuple[str, str]:
    token_id = str(uuid4())
    msg = f"{token_id}:{review_request_id}:{workspace_id}:{expires_at.isoformat()}"
    token_hash = hmac.new(secret_key, msg.encode(), hashlib.sha256).hexdigest()
    # URL token encodes both token_id and hash so the review page can look up and verify
    raw = f"{token_id}:{token_hash}"
    url_token = base64.urlsafe_b64encode(raw.encode()).decode().rstrip("=")
    return token_id, url_token

def validate_review_token(url_token: str, review_request: ReviewRequest, secret_key: bytes) -> bool:
    try:
        padded = url_token + "=" * (4 - len(url_token) % 4)
        raw = base64.urlsafe_b64decode(padded).decode()
        token_id, provided_hash = raw.split(":", 1)
    except Exception:
        return False
    if token_id != str(review_request.token_id):
        return False
    if datetime.utcnow() > review_request.expires_at.replace(tzinfo=None):
        return False
    if review_request.status != "pending":
        return False
    msg = f"{token_id}:{review_request.id}:{review_request.workspace_id}:{review_request.expires_at.isoformat()}"
    expected = hmac.new(secret_key, msg.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, provided_hash)
```

The `secret_key` is loaded from vault (Prompt 08) under the key `REVIEW_GATEWAY_HMAC_SECRET`. Generate a fresh 32-byte secret on first run via self-configuration (Prompt 16).

---

## Dispatch: Outbound Email

When a review request is created:

1. Render an HTML email using the template in `keprix/backend/review_gateway/templates/review_request.html`.
2. Subject: `[Action needed] {title} - review by {expires_at formatted as "Day DD Mon YYYY"}`
3. Body: context_message, artifact summary (first 400 chars if markdown, filename if PDF), and a prominent CTA button "Review and decide" linking to `{base_url}/review/{url_token}`.
4. Footer: "You were named as a reviewer by {workspace_name}. This link expires {expires_at}. If you did not expect this, you can ignore it."
5. Send via SMTP using the workspace SMTP credentials from vault. Fall back to the system SMTP config if no workspace SMTP is set.
6. Log the delivery attempt to `review_request.id` in the audit log (Prompt 02).

If `reviewer_webhook_url` is set, also POST a JSON payload:

```json
{
  "event": "review_requested",
  "review_request_id": "<uuid>",
  "title": "<title>",
  "context_message": "<message>",
  "review_url": "<url_with_token>",
  "expires_at": "<iso8601>",
  "reviewer_name": "<name>"
}
```

Sign the webhook POST with HMAC-SHA256 in the `X-keprix-Signature` header (same pattern as Scout policy receiver in Prompt 30).

---

## Dispatch: Reminder

If `reminder_at` is set and the request is still pending at that time, send an identical re-notification with subject prepended: `[Reminder] `.

Implement reminder dispatch in the cron service (Prompt 15):

```python
# runs every 5 minutes
async def fire_review_reminders():
    due = await db.fetchall(
        "SELECT * FROM review_requests WHERE status = 'pending' AND reminder_at <= NOW() AND reminder_at IS NOT NULL",
    )
    for req in due:
        await dispatch_review_notification(req)
        await db.execute(
            "UPDATE review_requests SET reminder_at = NULL WHERE id = $1", req.id
        )
```

---

## Dispatch: Expiry

A cron job (every 10 minutes) marks expired pending requests as `expired` and optionally sends an expiry notification to the workspace inbox (Prompt 24):

```python
async def expire_review_requests():
    expired = await db.fetchall(
        "SELECT * FROM review_requests WHERE status = 'pending' AND expires_at < NOW()"
    )
    for req in expired:
        await db.execute("UPDATE review_requests SET status = 'expired' WHERE id = $1", req.id)
        await inbox.notify(req.workspace_id, f"Review request '{req.title}' expired without a decision.")
        if req.playbook_run_id:
            await playbook_runtime.resume(req.playbook_run_id, req.playbook_step_id, {"action": "expired"})
```

---

## Public Review Page

`/review/{url_token}` - served without workspace authentication.

Behaviour:

1. Decode and validate token. If invalid or expired: show "This review link is no longer valid." with no further information.
2. If valid and pending: render `page_renderer.py` output with:
   - Workspace name (not workspace logo or full branding - just name).
   - Title and context message.
   - Artifact: if markdown, render as formatted HTML. If PDF, embed as `<iframe>` with download link. If URL, show as link with warning "This links to external content."
   - Reviewer name pre-filled (read-only).
   - Optional free-text note field (max 2000 chars).
   - Action buttons for each `allowed_action`.
3. On submit:
   - Validate token again (double-check status).
   - Record decision.
   - Invalidate token (set status to 'decided').
   - Resume playbook if attached.
   - Show confirmation: "Your decision has been recorded. You can close this page."
   - Send a copy of the decision to the reviewer's email as a receipt (their own record).

The page must work without JavaScript for accessibility. Forms use standard HTML POST. If JS is available, use it to enhance with loading state on the submit button only.

Page must have no keprix workspace navigation, no login prompt, and no cookies beyond a CSRF token for the form POST.

---

## API Endpoints (Authenticated, Workspace)

```
POST   /api/review-gateway/requests
       Body: { title, context_message, artifact_type, artifact_content|artifact_url|artifact_filename,
               reviewer_name, reviewer_email, reviewer_webhook_url?, allowed_actions?,
               expires_in_hours, reminder_in_hours?, playbook_run_id?, playbook_step_id? }
       Returns: { id, review_url, expires_at }

GET    /api/review-gateway/requests
       Query: status, page, page_size
       Returns: paginated list

GET    /api/review-gateway/requests/{id}
       Returns: full request record including decision if decided

DELETE /api/review-gateway/requests/{id}
       Cancels a pending request; sends cancellation email to reviewer
       Returns: { ok: true }
```

Public endpoint (no workspace auth):

```
GET    /review/{url_token}
       Returns: rendered HTML review page (not JSON)

POST   /review/{url_token}
       Body: form data { action, reviewer_note? }
       Returns: HTML confirmation page
```

---

## Playbook Step

Extend the durable playbook runtime (Prompt 51) with a `ReviewRequestStep`:

```python
class ReviewRequestStep(PlaybookStep):
    step_type = "review_request"

    async def execute(self, ctx: PlaybookContext) -> StepResult:
        req = await review_gateway.create_request(
            workspace_id=ctx.workspace_id,
            title=self.config["title"],
            context_message=self.config.get("context_message", ""),
            artifact_type=self.config["artifact_type"],
            artifact_content=ctx.resolve(self.config.get("artifact_content")),
            reviewer_name=self.config["reviewer_name"],
            reviewer_email=self.config["reviewer_email"],
            allowed_actions=self.config.get("allowed_actions", ["approve", "reject"]),
            expires_in_hours=self.config.get("expires_in_hours", 48),
            reminder_in_hours=self.config.get("reminder_in_hours"),
            playbook_run_id=ctx.run_id,
            playbook_step_id=self.step_id,
        )
        return StepResult(status="paused", metadata={"review_request_id": req.id})

    async def on_resume(self, ctx: PlaybookContext, resume_data: dict) -> StepResult:
        action = resume_data.get("action")
        note = resume_data.get("reviewer_note", "")
        ctx.set_variable("review_action", action)
        ctx.set_variable("reviewer_note", note)
        if action == "approve":
            return StepResult(status="success")
        elif action == "reject":
            return StepResult(status="failed", error=f"Reviewer rejected: {note}")
        else:
            # request_change or expired
            return StepResult(status="paused_for_changes", metadata={"note": note})
```

Playbook YAML syntax:

```yaml
steps:
  - id: cso_sign_off
    type: review_request
    title: "Hazard Log v1.4 - Clinical Safety Officer Sign-off"
    context_message: "Please review the attached Hazard Log and approve or reject before the release proceeds."
    artifact_type: pdf
    artifact_content: "{{ outputs.generate_hazard_log_pdf.url }}"
    reviewer_name: "{{ config.cso_name }}"
    reviewer_email: "{{ config.cso_email }}"
    allowed_actions: [approve, reject, request_change]
    expires_in_hours: 72
    reminder_in_hours: 48
```

---

## Workspace UI

`/settings/review-gateway` or `/review-gateway` (operator view):

- List of all review requests for the workspace (pending, decided, expired, cancelled).
- Each row: title, reviewer name, status, created_at, expires_at, decision if decided.
- Clicking a row shows the full detail including the artifact and decision note.
- "New review request" button (manual, not playbook-driven).
- Filter by status.

No reviewer management screen. Reviewers are named inline per request. This is intentional: the gateway is not a user directory.

---

## Security Requirements

- Review tokens must be single-use. Once a decision is submitted, any reuse of the same token returns HTTP 410 Gone.
- Tokens must not appear in server-side logs. Log only `token_id`, never the full URL token.
- The public review page must set `X-Frame-Options: DENY` and `Content-Security-Policy: default-src 'self'`.
- All review decisions are immutable once recorded. No update or delete endpoint for `review_decisions`.
- The reviewer's IP is hashed before storage (see Prompt 119 GDPR module). Never store plaintext IP.
- SMTP credentials are sourced from vault only (Prompt 08). Never accept SMTP password in the API request body.
- Rate limit `/review/{token}` to 10 GET and 5 POST requests per token per hour to prevent brute-force timing attacks.

---

## Acceptance Criteria

- Create a review request via API. Email arrives at the reviewer address with a working link.
- Reviewer opens link, sees the artifact, submits approval. Decision record is created. Token is invalidated.
- Attempting to use the same token a second time returns HTTP 410.
- A playbook with a ReviewRequestStep pauses when the step executes. After the reviewer approves, the playbook resumes from the correct step with `review_action = "approve"` in context.
- A request past `expires_at` is marked expired. Opening the expired token URL shows "no longer valid."
- Cancelling a pending request via DELETE sends a cancellation email and sets status to `cancelled`.
- The review page renders correctly with no JavaScript enabled.
- No SMTP credentials appear in any log line or API response.
- Reminder email fires when `reminder_at` passes and request is still pending.
