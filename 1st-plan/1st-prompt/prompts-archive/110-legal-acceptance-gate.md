# keprix - Prompt 110: Legal Acceptance Gate

## Context

Read `02-security-foundation-and-platform-hardening.md`, `31-frontend-ui-and-launchers.md`, and `88-gdpr-compliance-infrastructure.md`.

keprix is deployed by operators who use it to process business data. When keprix is offered as a service (or when an operator distributes a keprix-based product to their own users), those users must be able to confirm that they have read and accepted the relevant legal terms before the product processes any of their data.

This is not a UX nicety. For regulated deployments (healthcare, legal, finance), the acceptance record is required evidence of lawful basis under GDPR. It must be:
- Versioned: each time terms change, existing acceptances do not carry forward.
- Timestamped: exact date and time of acceptance.
- Auditable: exportable for regulatory review.
- Enforced: the workspace is inaccessible until acceptance is recorded.

This prompt builds that infrastructure for keprix: the database schema, the API middleware, the gate UI, and the admin export. It also wires into the GDPR consent ledger (Prompt 119) so that acceptance is recorded as a `data_processing` consent event.

---

## File Structure

```
keprix/backend/legal/
    __init__.py
    models.py           - DB models for policy versions and acceptances
    middleware.py       - FastAPI middleware that blocks unauthenticated or unaccepted sessions
    routes.py           - API endpoints for accepting terms and querying acceptance status
    schemas.py          - Pydantic schemas
    policy_store.py     - Loads current policy version from config or file

keprix/tests/legal/
    test_middleware.py
    test_routes.py
    test_policy_store.py

keprix/ui/web/src/app/legal/
    accept/page.tsx     - full-screen acceptance gate shown before workspace access
    [type]/page.tsx     - renders the full text of a named policy (e.g. /legal/terms, /legal/privacy)

keprix/ui/web/src/app/(workspace)/settings/legal/
    page.tsx            - operator view: current policy versions, acceptance log, export
```

---

## Database

```sql
CREATE TABLE legal_policies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    policy_type TEXT NOT NULL,
    -- 'terms_of_use', 'privacy_policy', 'data_processing_agreement', 'acceptable_use'
    version TEXT NOT NULL,
    -- semver-style string e.g. '2025-06-01' or '1.3.0'
    title TEXT NOT NULL,
    summary TEXT,
    -- short plain-language summary shown in the gate UI before full text
    full_text_url TEXT,
    -- URL to the full policy text (can be a /legal/{type} route or external URL)
    published_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    requires_re_acceptance BOOLEAN NOT NULL DEFAULT TRUE,
    -- if true, all existing acceptances for this type become stale on publish
    active BOOLEAN NOT NULL DEFAULT FALSE,
    -- only one active policy per type at a time
    UNIQUE (policy_type, version)
);

CREATE TABLE legal_acceptances (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL,
    user_id UUID,
    -- null for API callers (keyed by api_caller_id instead)
    api_caller_id TEXT,
    policy_type TEXT NOT NULL,
    policy_version TEXT NOT NULL,
    accepted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    accepted_ip_hash TEXT,
    -- hashed per Prompt 119 ip_hashing.py
    user_agent_hash TEXT,
    source TEXT NOT NULL DEFAULT 'web_gate',
    -- 'web_gate', 'api', 'cli', 'admin_on_behalf'
    UNIQUE (workspace_id, user_id, policy_type, policy_version)
);

CREATE INDEX ON legal_acceptances(workspace_id, user_id);
CREATE INDEX ON legal_acceptances(policy_type, policy_version);
CREATE INDEX ON legal_policies(policy_type, active);
```

---

## Policy Version Management

Policy versions are configured in `keprix/config/legal_policies.yaml`. Each keprix operator sets their own policies for their deployment. The config file structure:

```yaml
policies:
  terms_of_use:
    version: "2025-09-01"
    title: "Terms of Use"
    summary: "By using this system you agree to use it lawfully and not attempt to extract or misuse data held by others."
    full_text_url: "/legal/terms"
    requires_re_acceptance: true
    active: true

  privacy_policy:
    version: "2025-09-01"
    title: "Privacy Policy"
    summary: "We store data you provide to operate the service. See the full policy for details."
    full_text_url: "/legal/privacy"
    requires_re_acceptance: true
    active: true

  data_processing_agreement:
    version: "2025-09-01"
    title: "Data Processing Agreement"
    summary: "Required for organisations processing personal data. This agreement defines our roles as processor and your role as controller."
    full_text_url: "/legal/dpa"
    requires_re_acceptance: true
    active: true
```

The full text of each policy is served from `keprix/ui/web/src/app/legal/[type]/page.tsx`, which reads from `keprix/config/legal_text/{type}.md`. Operators replace these Markdown files with their own legal text before deploying.

Syncing: on startup, `policy_store.py` reads `legal_policies.yaml` and upserts into `legal_policies` table. Conflicts on `(policy_type, version)` are ignored; only new versions are inserted.

---

## Middleware (`middleware.py`)

The middleware runs after authentication on every authenticated API route.

Logic:

```python
async def legal_gate_middleware(request: Request, call_next):
    if not requires_legal_check(request.url.path):
        return await call_next(request)

    user = request.state.user
    if user is None:
        return await call_next(request)

    active_policies = await policy_store.get_active_policies()
    missing = []
    for policy in active_policies:
        accepted = await db.fetchone(
            "SELECT id FROM legal_acceptances WHERE workspace_id = $1 AND user_id = $2 AND policy_type = $3 AND policy_version = $4",
            user.workspace_id, user.id, policy.policy_type, policy.version,
        )
        if not accepted:
            missing.append(policy.policy_type)

    if missing:
        return JSONResponse(
            status_code=451,  # Unavailable For Legal Reasons
            content={
                "error": "legal_acceptance_required",
                "message": "You must accept the current policies before continuing.",
                "pending_policies": missing,
                "accept_url": "/legal/accept",
            }
        )

    return await call_next(request)
```

Use HTTP 451 (Unavailable For Legal Reasons) - the semantically correct status code for this scenario.

Routes exempt from the gate check:

```python
EXEMPT_PATHS = {
    "/api/legal/",          # acceptance and policy routes themselves
    "/api/health",
    "/api/auth/",
    "/legal/",              # policy text pages
    "/review/",             # external reviewer pages (Prompt 117)
    "/api/scout/webhook",   # Scout inbound
}
```

The check is path-prefix based. Any path starting with an exempt prefix is allowed through.

---

## Gate UI (`/legal/accept`)

A full-screen page with no workspace navigation, no sidebar. Shown when the API returns HTTP 451.

Layout:

```
[Product name / workspace name]

You must accept the following policies to continue:

[ ] Terms of Use (version 2025-09-01)
    By using this system you agree to use it lawfully...
    [Read full Terms of Use ↗]

[ ] Privacy Policy (version 2025-09-01)
    We store data you provide to operate the service...
    [Read full Privacy Policy ↗]

[ ] Data Processing Agreement (version 2025-09-01)
    Required for organisations processing personal data...
    [Read full Data Processing Agreement ↗]

By clicking "Accept and continue" you confirm that you have read and accept all of the above policies.

[Accept and continue]
```

Checkboxes are required: the "Accept and continue" button is disabled until all are checked. Each policy link opens in a new tab.

On submit: POST to `/api/legal/accept` with the list of accepted policy types. On success: redirect to the intended destination or `/` (workspace home).

The gate page must be accessible without JavaScript: use standard HTML form with server-side redirect. Enhance with JS for UX (button disable state, smooth redirect) but do not require it.

---

## API Endpoints

```
GET  /api/legal/policies
     Returns: list of active policies with version, title, summary, full_text_url
     No auth required.

GET  /api/legal/status
     Requires workspace auth.
     Returns: { pending: [{ policy_type, version, title }], all_accepted: bool }

POST /api/legal/accept
     Requires workspace auth.
     Body: { policy_types: ['terms_of_use', 'privacy_policy', 'data_processing_agreement'] }
     Records acceptance for each named type at its current active version.
     Also records each as a 'data_processing' consent event in the GDPR consent ledger (Prompt 119).
     Returns: { accepted: [policy_type], all_accepted: bool }

GET  /api/legal/acceptances
     Requires workspace auth + admin role.
     Query: page, page_size, policy_type, policy_version
     Returns: paginated list of legal_acceptances for this workspace (admin view)

GET  /api/legal/acceptances/export
     Requires workspace auth + admin role.
     Returns: CSV download of all acceptances for this workspace
     Columns: user_id, policy_type, policy_version, accepted_at, source
     (No PII beyond user_id; IP is stored hashed and is included as ip_hash)
```

---

## CLI Acceptance Flow

When running keprix via CLI (Prompt 23) and the server returns HTTP 451, the CLI must:

1. Print: "Legal acceptance required. The following policies must be accepted before you can use keprix:"
2. List each pending policy with its summary.
3. Prompt: "Type 'accept' to accept all policies, or 'exit' to quit: "
4. If user types 'accept': POST to `/api/legal/accept` and continue.
5. If user types anything else: exit with code 1.

CLI acceptance is recorded with `source: 'cli'`.

---

## Admin On-Behalf Acceptance

In rare cases (bulk onboarding, user cannot access the web UI), an admin may record acceptance on behalf of a user:

```
POST /api/legal/accept-on-behalf
     Requires workspace auth + super-admin role.
     Body: { user_id, policy_types, reason }
     Records with source: 'admin_on_behalf'
     Logs the action to audit log (Prompt 02) with the admin's user_id and reason.
```

This must be explicitly logged and is not available for self-service use.

---

## GDPR Ledger Integration

Every acceptance also records to the GDPR consent ledger (Prompt 119):

```python
await consent.record_consent(
    workspace_id=user.workspace_id,
    subject_type="operator",
    subject_identifier=user.id,
    purpose="data_processing",
    lawful_basis="consent",
    granted=True,
    version=policy.version,
    source="legal_gate",
    ip=request.client.host,  # will be hashed inside record_consent
    user_agent=request.headers.get("User-Agent"),
)
```

When a user's workspace is erased (Prompt 119 erasure module), their legal acceptance records are anonymised, not deleted. The fact of acceptance (timestamp, policy version) is retained. The user_id field is replaced with `[ERASED]`.

---

## Acceptance Criteria

- Authenticated API requests return HTTP 451 when the user has not accepted all active policies.
- The gate UI shows all pending policies with summaries and links to full text.
- Submitting the gate form without checking all checkboxes does not proceed.
- Submitting with all checked records acceptance and allows the request to continue.
- Acceptance is recorded in `legal_acceptances` and in `privacy_consent_ledger`.
- A new policy version published (new row in `legal_policies` with `active: true` for the type) requires all users to re-accept on next login.
- `GET /api/legal/status` returns the correct pending list before acceptance and `all_accepted: true` after.
- `GET /api/legal/acceptances/export` returns a CSV with correct columns and no plaintext IP addresses.
- CLI: typing 'accept' at the prompt records acceptance and allows the CLI command to proceed.
- Exempt routes (health, legal, auth, external review pages) are accessible without acceptance.
- The gate page renders and the form submits correctly with JavaScript disabled.
