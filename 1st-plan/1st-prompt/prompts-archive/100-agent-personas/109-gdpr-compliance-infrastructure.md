# keprix - Prompt 109: GDPR Compliance Infrastructure

## Context

Read `02-security-foundation-and-platform-hardening.md`, `08-vault-credentials-and-secrets.md`, `16-api-surface-and-observability.md`, and `89-legal-acceptance-gate.md`.

keprix stores data on behalf of operators who use it to process information. Even when keprix does not handle patient data or personal data directly, the organisations deploying it are subject to data protection law. The UK GDPR, EU GDPR, and equivalent laws require that any software system used by a regulated organisation can:

1. Export all data held about a subject (Data Subject Access Request, DSAR).
2. Delete all data linked to a subject on request (Right to Erasure).
3. Demonstrate a lawful basis for processing (consent record or legitimate interest log).
4. Not retain unnecessary personal data in system logs.

This prompt builds those capabilities into keprix as a standard infrastructure module. It is not optional or plugin-based. GDPR infrastructure is as core as authentication.

Scope: keprix's own data - run logs, memory, documents, notes, contacts, credentials metadata, agent messages, audit records. Not the content of external systems keprix connects to; those are the operator's responsibility.

---

## File Structure

```
keprix/backend/privacy/
    __init__.py
    ip_hashing.py       - consistent reversible-free IP hashing for log entries
    consent.py          - consent ledger: record, check, and revoke consent events
    dsar.py             - data subject access request: collect and export all held data
    erasure.py          - right to erasure: hard delete or anonymise held data by subject
    retention.py        - configurable retention policy enforcement (cron job)
    routes.py           - API endpoints for GDPR operations
    schemas.py          - Pydantic schemas
    export_builder.py   - assembles DSAR export zip (calls dsar.py, export module Prompt 118)

keprix/tests/privacy/
    test_ip_hashing.py
    test_consent.py
    test_dsar.py
    test_erasure.py
    test_retention.py

keprix/ui/web/src/app/(workspace)/settings/privacy/
    page.tsx            - privacy centre for operators: GDPR controls, retention settings
```

---

## Database

```sql
CREATE TABLE privacy_consent_ledger (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL,
    subject_type TEXT NOT NULL,
    -- 'operator', 'end_user', 'contact', 'api_caller'
    subject_identifier TEXT NOT NULL,
    -- email or hashed ID depending on subject_type
    purpose TEXT NOT NULL,
    -- e.g. 'data_processing', 'analytics', 'marketing_comms'
    lawful_basis TEXT NOT NULL,
    -- 'consent', 'legitimate_interest', 'contract', 'legal_obligation', 'vital_interests', 'public_task'
    granted BOOLEAN NOT NULL,
    -- false = withdrawn
    version TEXT,
    -- version of the terms/policy accepted
    source TEXT NOT NULL,
    -- 'legal_gate', 'api', 'explicit_in_app', 'operator_configured'
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ip_hash TEXT,
    user_agent_hash TEXT
);

CREATE TABLE privacy_erasure_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL,
    subject_type TEXT NOT NULL,
    subject_identifier TEXT NOT NULL,
    requested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    tables_affected TEXT[],
    rows_affected INTEGER,
    requested_by_user_id UUID,
    status TEXT NOT NULL DEFAULT 'pending'
    -- 'pending', 'processing', 'complete', 'partial', 'error'
);

CREATE TABLE privacy_dsar_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL,
    subject_type TEXT NOT NULL,
    subject_identifier TEXT NOT NULL,
    requested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    export_file_id UUID,
    requested_by_user_id UUID,
    status TEXT NOT NULL DEFAULT 'pending'
);

CREATE TABLE privacy_retention_policy (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL,
    data_category TEXT NOT NULL,
    -- 'run_logs', 'agent_messages', 'audit_log', 'contacts', 'documents', 'memory_episodes'
    retain_days INTEGER NOT NULL,
    -- -1 means retain indefinitely
    action TEXT NOT NULL DEFAULT 'anonymise',
    -- 'anonymise' or 'delete'
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (workspace_id, data_category)
);

CREATE INDEX ON privacy_consent_ledger(workspace_id, subject_identifier);
CREATE INDEX ON privacy_erasure_log(workspace_id, status);
```

---

## IP Hashing (`ip_hashing.py`)

All modules in keprix that log an IP address MUST call `hash_ip` before storage. Never store a raw IP address in any table.

```python
import hashlib, hmac

def hash_ip(ip: str, workspace_id: str, secret: bytes) -> str:
    """
    HMAC-SHA256 of (ip + workspace_id). Per-workspace salt means
    IPs are not linkable across workspaces. One-way: cannot reverse.
    """
    msg = f"{workspace_id}:{ip}".encode()
    return hmac.new(secret, msg, hashlib.sha256).hexdigest()
```

The `secret` is loaded from vault under `PRIVACY_IP_HASH_SECRET`. Generated on first run (Prompt 16). The secret must be the same across restarts so that identical IP + workspace combinations produce the same hash (needed for rate limiting and review gateway fraud detection).

Modules that must switch to `hash_ip` before storing:
- Audit log (Prompt 02): `ip_address` column.
- Review gateway (Prompt 117): `reviewer_ip_hash` column.
- Legal acceptance gate (Prompt 130): `accepted_ip_hash` column.
- API request log (Prompt 18): any per-request IP column.
- Run logs: any IP field.

---

## Consent Ledger (`consent.py`)

```python
async def record_consent(
    workspace_id: str,
    subject_type: str,
    subject_identifier: str,
    purpose: str,
    lawful_basis: str,
    granted: bool,
    version: str | None = None,
    source: str = "api",
    ip: str | None = None,
    user_agent: str | None = None,
) -> str:
    """Records a consent event. Returns the ledger entry ID."""

async def has_consent(
    workspace_id: str,
    subject_identifier: str,
    purpose: str,
) -> bool:
    """Returns True if the most recent consent entry for this subject and purpose is granted=True."""

async def withdraw_consent(
    workspace_id: str,
    subject_identifier: str,
    purpose: str,
    source: str = "api",
) -> None:
    """Records a granted=False entry. Does not delete prior entries (immutable ledger)."""

async def get_consent_history(
    workspace_id: str,
    subject_identifier: str,
) -> list[ConsentEntry]:
    """Returns the full consent history for audit."""
```

The consent ledger is append-only. Never update or delete rows. The current state for a subject + purpose is determined by the most recent row's `granted` field.

---

## Data Subject Access Request (`dsar.py`)

When an operator triggers a DSAR for a subject identifier, the module must:

1. Query every data-holding table in keprix for rows linked to `subject_identifier`.
2. Collect the results into a structured JSON manifest.
3. Call the export module (Prompt 118) to render the manifest as a formatted PDF summary.
4. Assemble a zip: `manifest.json` (full machine-readable data) + `summary.pdf` (human-readable) + any document or note files linked to the subject.
5. Store the zip in the workspace file store.
6. Record completion in `privacy_dsar_log`.

Tables to scan (by default - extend as new modules add personal data tables):

```python
DSAR_QUERIES = {
    "agent_messages":   "SELECT * FROM agent_messages WHERE workspace_id = $1 AND (metadata->>'user_id' = $2 OR metadata->>'email' = $2)",
    "audit_log":        "SELECT * FROM audit_log WHERE workspace_id = $1 AND actor_id = $2",
    "contacts":         "SELECT * FROM contacts WHERE workspace_id = $1 AND (email = $2 OR id = $2)",
    "consent_ledger":   "SELECT * FROM privacy_consent_ledger WHERE workspace_id = $1 AND subject_identifier = $2",
    "review_decisions": "SELECT * FROM review_decisions WHERE review_request_id IN (SELECT id FROM review_requests WHERE workspace_id = $1) AND (reviewer_email = $2 OR token_id::text = $2)",
    "legal_acceptance": "SELECT * FROM legal_acceptances WHERE workspace_id = $1 AND user_id = $2",
    "memory_episodes":  "SELECT * FROM memory_episodes WHERE workspace_id = $1 AND (metadata->>'user_id' = $2 OR content ILIKE '%' || $2 || '%')",
}
```

Operators can extend `DSAR_QUERIES` via the workspace settings (add custom SQL queries for domain-pack tables). Custom queries must be whitelisted per query pattern; arbitrary SQL is not accepted.

DSAR export must complete within 30 minutes for any workspace. Log a warning if it takes more than 5 minutes.

---

## Right to Erasure (`erasure.py`)

```python
async def erase_subject(
    workspace_id: str,
    subject_type: str,
    subject_identifier: str,
    requested_by_user_id: str,
    dry_run: bool = False,
) -> ErasureReport:
    """
    Anonymises or deletes all records linked to subject_identifier in this workspace.
    If dry_run=True, returns a report of what would be affected without making changes.
    """
```

Erasure strategy: **anonymise by default, hard-delete on request**.

Anonymise means:
- Text fields containing the subject identifier: replace with `[ERASED]`.
- Email fields: replace with a one-way hash of the email (not the IP hash; a different purpose-specific hash).
- Name fields: replace with `[ERASED]`.
- Free-text content fields (messages, notes, documents): set to `[Content erased on request under right to erasure]`.

Hard delete means: `DELETE FROM table WHERE ...`. Only used when the operator explicitly chooses this mode and confirms.

Tables with immutable rows (audit log, consent ledger, erasure log itself):
- Do not delete rows from these tables. Anonymise the personal data fields within them.
- The fact that a record existed (timestamps, IDs) is retained for legal and audit reasons.

After erasure:
- Record completion in `privacy_erasure_log`.
- Send a confirmation notification to the workspace inbox (Prompt 24).
- If Scout is connected (Prompt 30), emit a `gdpr_erasure_complete` event to Scout.

---

## Retention Policy (`retention.py`)

Default retention periods (applied if the operator has not configured custom policy):

| Data category       | Default retain | Default action |
|---------------------|----------------|----------------|
| run_logs            | 90 days        | anonymise      |
| agent_messages      | 365 days       | anonymise      |
| audit_log           | 730 days       | anonymise      |
| contacts            | indefinite     | n/a            |
| documents           | indefinite     | n/a            |
| memory_episodes     | 365 days       | anonymise      |

A cron job (Prompt 15) runs daily and applies the policy:

```python
async def enforce_retention():
    policies = await db.fetchall("SELECT * FROM privacy_retention_policy")
    for policy in policies:
        if policy.retain_days == -1:
            continue
        cutoff = datetime.utcnow() - timedelta(days=policy.retain_days)
        if policy.action == "anonymise":
            await anonymise_old_rows(policy.workspace_id, policy.data_category, cutoff)
        elif policy.action == "delete":
            await delete_old_rows(policy.workspace_id, policy.data_category, cutoff)
```

Operators can override retention periods per category in the privacy settings UI. Minimum allowed: 30 days (to allow incident investigation). Maximum: unlimited.

---

## API Endpoints

All require workspace authentication and at least operator-level role.

```
GET    /api/privacy/consent
       Query: subject_identifier
       Returns: consent history for that subject

POST   /api/privacy/consent
       Body: { subject_type, subject_identifier, purpose, lawful_basis, granted, version?, source? }
       Returns: { id }

POST   /api/privacy/dsar
       Body: { subject_type, subject_identifier }
       Returns: { dsar_log_id, status: 'processing' }
       (async; poll /api/privacy/dsar/{id} for completion)

GET    /api/privacy/dsar/{id}
       Returns: { status, export_file_url? }

POST   /api/privacy/erasure
       Body: { subject_type, subject_identifier, mode: 'anonymise'|'delete', dry_run?: bool }
       Returns: { erasure_log_id, rows_affected, tables_affected }

GET    /api/privacy/erasure/{id}
       Returns: { status, completed_at?, tables_affected, rows_affected }

GET    /api/privacy/retention
       Returns: workspace retention policy (all categories)

PUT    /api/privacy/retention/{data_category}
       Body: { retain_days, action }
       Returns: { ok: true }

GET    /api/privacy/health
       Returns: summary of GDPR module status (last retention run, pending DSARs, pending erasures)
```

---

## Privacy Centre UI (`/settings/privacy`)

Sections:

**Data Retention**: Table of all data categories with current retain_days and action. Editable per row. "Last enforcement run" timestamp shown.

**Consent Records**: Search by subject identifier. View full consent history. Button to record withdrawal.

**Data Subject Requests**: Button "Process DSAR". Input: subject_identifier, subject_type. Shows recent DSARs with download links for completed exports.

**Erasure Requests**: Button "Erase subject data". Input: subject_identifier. Dry-run first (shows what will be affected), then confirm to apply. Shows recent erasure log.

**Audit**: Link to audit log (Prompt 02) filtered to privacy-related events.

---

## Scout Integration

When Scout is connected (Prompt 30), emit these events:

| Event type            | When                              |
|-----------------------|-----------------------------------|
| `gdpr_dsar_requested` | DSAR is triggered                 |
| `gdpr_dsar_complete`  | DSAR export is ready              |
| `gdpr_erasure_complete` | Erasure is complete             |
| `gdpr_retention_run`  | Daily retention enforcement runs  |
| `gdpr_consent_withdrawn` | Consent is withdrawn           |

Use the standard Scout event payload schema (see Prompt 131 for the clinical event taxonomy; GDPR events use the same envelope).

---

## Acceptance Criteria

- `hash_ip` produces a consistent hash for the same IP + workspace + secret across restarts.
- Different workspaces produce different hashes for the same IP.
- DSAR triggered for a subject identifier returns a zip containing `manifest.json` and `summary.pdf` within 5 minutes for a workspace with up to 10,000 records.
- Erasure with `dry_run: true` returns an accurate count of rows that would be affected without modifying any data.
- Erasure with `dry_run: false` replaces personal data fields with `[ERASED]`. Email fields are hashed.
- Audit log rows are not deleted during erasure; personal data fields within them are anonymised.
- Retention policy enforcement runs and logs completion. Run logs older than `retain_days` are anonymised or deleted per policy.
- Consent ledger is append-only: no UPDATE or DELETE ever runs on `privacy_consent_ledger`.
- Privacy centre UI allows viewing and editing retention policy, triggering DSAR, and triggering erasure.
- `GET /api/privacy/health` returns a response that includes the last retention run timestamp.
