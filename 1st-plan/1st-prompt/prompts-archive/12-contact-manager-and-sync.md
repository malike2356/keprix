# keprix - Prompt 12: Contact Manager and Sync

## Purpose

Build the contact manager for keprix. This is the module that lets the agent
look up people by name and take action on them: send an email, initiate a call, or
open a conversation on a messaging channel.

Build this after Prompt 11 (email) and before using Prompt 13 (messaging gateway),
because the email send step in the agent confirmation flow delegates to the email
module, and the call initiation step optionally delegates to the messaging gateway.

## What This Prompt Builds

1. A local contact store synced from external sources.
2. Sync connectors: Google Contacts, Microsoft Outlook/365, CardDAV, vCard import, CSV import.
3. Agent contact tools: fuzzy name search and disambiguation.
4. The email confirmation flow: find contact, confirm, draft, read back, send.
5. The call initiation flow: find contact, confirm, call (Twilio) or present number.
6. A per-user preference for confirmation behaviour.
7. A contacts UI page in the workspace.

---

## Database Schema

`backend/contacts/models.py`

```sql
CREATE TABLE contacts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    display_name TEXT NOT NULL,
    given_name TEXT,
    family_name TEXT,
    emails JSONB NOT NULL DEFAULT '[]',
    -- [{address: string, label: string, primary: boolean}]
    phones JSONB NOT NULL DEFAULT '[]',
    -- [{number: string, label: string, primary: boolean}]
    addresses JSONB NOT NULL DEFAULT '[]',
    organisation TEXT,
    job_title TEXT,
    notes TEXT,
    photo_url TEXT,
    source TEXT NOT NULL DEFAULT 'manual',
    -- 'google', 'microsoft', 'carddav', 'vcf', 'csv', 'manual'
    source_id TEXT,
    -- external ID from the sync source. NULL for manual contacts.
    source_etag TEXT,
    -- sync delta token per contact (Google uses etag, Microsoft uses @odata.etag)
    last_synced_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(source, source_id)
);

CREATE INDEX ON contacts (display_name);
CREATE INDEX ON contacts (family_name, given_name);
CREATE INDEX ON contacts USING GIN (emails);
CREATE INDEX ON contacts USING GIN (phones);

CREATE TABLE contact_sync_sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    provider TEXT NOT NULL,
    -- 'google', 'microsoft', 'carddav'
    display_name TEXT NOT NULL,
    -- e.g. "Work Google Account", "Personal Outlook"
    vault_token_id UUID,
    -- references the OAuth token stored in the vault (Prompt 08)
    carddav_url TEXT,
    -- CardDAV only: server URL
    carddav_username TEXT,
    -- CardDAV only
    sync_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    sync_interval_minutes INT NOT NULL DEFAULT 60,
    last_full_sync_at TIMESTAMPTZ,
    last_delta_sync_at TIMESTAMPTZ,
    last_sync_error TEXT,
    contact_count INT DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE contact_action_preferences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL UNIQUE,
    confirm_before_email BOOLEAN NOT NULL DEFAULT TRUE,
    -- true: agent reads back draft and waits for approval before sending
    confirm_before_call BOOLEAN NOT NULL DEFAULT TRUE,
    -- true: agent confirms the number before initiating a call
    read_back_draft BOOLEAN NOT NULL DEFAULT TRUE,
    -- true: agent reads out the email draft in the chat before asking to send
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

---

## Sync Connectors

`backend/contacts/sync/`

Each connector implements the same interface:

```python
class ContactSyncConnector(ABC):
    async def full_sync(self, source: ContactSyncSource) -> SyncResult:
        """Fetch all contacts from the source and upsert into local store."""

    async def delta_sync(self, source: ContactSyncSource) -> SyncResult:
        """Fetch only contacts changed since last sync."""

    async def get_auth_url(self) -> str:
        """Return the OAuth2 authorization URL (Google and Microsoft only)."""

    async def exchange_code(self, code: str) -> OAuthToken:
        """Exchange authorization code for tokens and store in vault."""
```

### Google Contacts (People API)

`backend/contacts/sync/google.py`

- OAuth2 scope: `https://www.googleapis.com/auth/contacts.readonly`
- API: Google People API v1
- Full sync: `GET people.connections.list?personFields=names,emailAddresses,phoneNumbers,organizations,addresses,photos`
- Delta sync: reuse `syncToken` from previous response
- Store `syncToken` in `contact_sync_sources.last_delta_sync_at` metadata
- Map `resourceName` to `source_id`, `etag` to `source_etag`

OAuth flow:
1. User clicks "Connect Google Contacts" in the sync settings UI.
2. Agent opens the OAuth consent screen (`GET /api/contacts/sync/google/auth`).
3. Google redirects to `/api/contacts/sync/google/callback?code=...`.
4. Server exchanges code for token and stores in vault (Prompt 08).
5. Agent triggers a full sync immediately.

### Microsoft Outlook / Microsoft 365

`backend/contacts/sync/microsoft.py`

- OAuth2 scope: `Contacts.Read` (Microsoft Graph)
- API: `GET /me/contacts?$select=displayName,givenName,surname,emailAddresses,businessPhones,mobilePhone,jobTitle,companyName`
- Delta sync: `GET /me/contacts/delta` using `@odata.deltaLink` stored between syncs
- Map `id` to `source_id`, `@odata.etag` to `source_etag`

OAuth flow: same pattern as Google, endpoint prefix `/api/contacts/sync/microsoft/`.

### CardDAV

`backend/contacts/sync/carddav.py`

Supports: Apple iCloud Contacts, Nextcloud, Fastmail, ProtonMail (via bridge), Radicale.

- Library: `aiohttp` for HTTP, parse vCard 3.0/4.0 with `vobject`
- Discovery: `PROPFIND` on the server URL to find address books
- Full sync: `REPORT` with `addressbook-query` to fetch all vCards
- Delta sync: `REPORT` with `sync-collection` (WebDAV sync, RFC 6578)
- Username/password stored in vault. No OAuth for CardDAV.

Setup:
1. User provides server URL, username, password in settings.
2. Server tests connection and discovers address books.
3. User selects which address book(s) to sync.

### vCard File Import

`backend/contacts/sync/vcf.py`

- Accept `.vcf` file upload (single or multi-contact vCard)
- Parse with `vobject`
- Upsert into contacts table with `source = 'vcf'`
- Duplicates: match on email address before inserting (avoid duplicating a contact already synced from Google)
- Return import summary: added, updated, skipped

### CSV Import

`backend/contacts/sync/csv_import.py`

Smart header mapping. Recognise common export formats:

| Format | Detected by |
| --- | --- |
| Google Contacts CSV | Header contains "Given Name", "Family Name", "E-mail 1 - Value" |
| Outlook CSV | Header contains "First Name", "Last Name", "E-mail Address" |
| Generic | Best-effort mapping on first pass, user confirms column mapping |

Duplicate detection: match on primary email before inserting.

---

## Agent Contact Tools

`backend/contacts/tools.py`

These are registered in the keprix tool registry (Prompt 05) so the agent can call them.

### `contact_search`

```python
async def contact_search(query: str, limit: int = 5) -> list[ContactResult]:
    """
    Fuzzy search contacts by name, organisation, email, or phone.
    Returns ranked results. Uses trigram similarity (pg_trgm) on display_name,
    phonetic matching (Metaphone) on names, and exact match on email/phone.
    """
```

Ranking:
1. Exact name match (highest)
2. Starts-with match on family_name or given_name
3. Trigram similarity on display_name (pg_trgm)
4. Phonetic match (Metaphone): "Jon" matches "John", "Malike" matches "Malik"
5. Organisation match
6. Email/phone substring match

Enable `pg_trgm` extension: `CREATE EXTENSION IF NOT EXISTS pg_trgm;`

### `contact_get`

```python
async def contact_get(contact_id: str) -> Contact | None:
    """Fetch a single contact by ID."""
```

### `contact_get_primary_email`

```python
async def contact_get_primary_email(contact_id: str) -> str | None:
    """Return the primary email address, or the first email if no primary is set."""
```

### `contact_get_primary_phone`

```python
async def contact_get_primary_phone(contact_id: str) -> str | None:
    """Return the primary phone number, or the first phone if no primary is set."""
```

---

## Agent Behaviours

These are not new tools - they are patterns the agent follows using the tools above
combined with the email module (Prompt 11) and the messaging gateway (Prompt 13).
Document them here so the agent system prompt and skill definitions cover them correctly.

### Email Flow

The agent always follows this sequence when instructed to email someone:

```
User: "Email Marcus about the invoice"

Step 1: Search
  Agent: [calls contact_search("Marcus")]

Step 2a: Single clear match
  Agent: "I found Marcus Osei (marcus.osei@company.com). Is that who you mean?"
  User: "yes" / "yeah" / "correct"

Step 2b: Multiple matches
  Agent: "I found a few people named Marcus:
          1. Marcus Osei - marcus.osei@company.com (Verlox Ltd)
          2. Marcus Brown - m.brown@agency.co.uk
          3. Marcus Adebayo - madebayo@techco.io

          Which one?"
  User: "the first one" / "Marcus Osei" / "1"

Step 2c: No match
  Agent: "I couldn't find anyone named Marcus in your contacts.
          Do you want me to search by email address, or add them as a new contact?"

Step 3: Draft
  Agent: [drafts the email based on the user's instruction and context]

Step 4: Read back (if read_back_draft = true)
  Agent: "Here is the draft:

  ---
  To: Marcus Osei <marcus.osei@company.com>
  Subject: Invoice Follow-up

  Hi Marcus,

  I wanted to follow up on the invoice we discussed. Could you let me know
  the current status?

  Best regards,
  [User name]
  ---

  Should I send this, or would you like to change anything?"

Step 5a: User approves
  User: "send it" / "looks good" / "yes" / "go ahead"
  Agent: [sends via email module] "Sent to Marcus Osei."

Step 5b: User edits
  User: "change the subject to Invoice #1042"
  Agent: [updates draft, reads back again]

Step 5c: User cancels
  User: "cancel" / "never mind"
  Agent: "Cancelled. The email was not sent."
```

When `confirm_before_email = false` (user has disabled confirmation):

```
User: "Email Marcus about the invoice"
Agent: [searches, finds Marcus, drafts, sends]
Agent: "Sent to Marcus Osei (marcus.osei@company.com).

Subject: Invoice Follow-up
[first 2 lines of email for awareness]

Let me know if you need anything changed."
```

### Call Flow

```
User: "Call Sarah"

Step 1: Search
  Agent: [calls contact_search("Sarah")]

Step 2a: Single match
  Agent: "I found Sarah Johnson (+44 7911 123456). Shall I call her?"
  User: "yes"

Step 2b: Multiple matches
  Agent: "I found 2 Sarahs:
          1. Sarah Johnson - +44 7911 123456 (mobile)
          2. Sarah Ahmed - +44 20 7946 0001 (work)
          Which one?"

Step 3a: Twilio configured in vault
  Agent: [initiates outbound Twilio voice call]
  Agent: "Calling Sarah Johnson now. I'll let you know if it connects."

Step 3b: No Twilio (fallback)
  Agent: "To call Sarah Johnson, the number is +44 7911 123456.
          [Open in dialer]  [Copy number]"
```

When `confirm_before_call = false`:

```
User: "Call Sarah"
Agent: [searches, finds Sarah, initiates call immediately]
Agent: "Calling Sarah Johnson (+44 7911 123456)."
```

### Preference Commands

The agent updates `contact_action_preferences` when the user gives these instructions:

| User says | What changes |
| --- | --- |
| "send without confirmation" / "stop asking me to confirm emails" | `confirm_before_email = false` |
| "always confirm before sending" / "ask me before you send emails" | `confirm_before_email = true` |
| "call without asking" / "just call, don't confirm" | `confirm_before_call = false` |
| "always confirm before calling" | `confirm_before_call = true` |
| "don't read back drafts" | `read_back_draft = false` |
| "read back emails before sending" | `read_back_draft = true` |

The agent confirms the change: "Understood. I'll send emails without asking for
confirmation from now on. You can change this anytime by saying 'always confirm
before sending'."

---

## Call Initiation (Twilio)

`backend/contacts/call.py`

```python
async def initiate_call(to_number: str, from_number: str) -> CallResult:
    """
    Initiate an outbound voice call via Twilio Programmable Voice.
    Requires TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, and TWILIO_FROM_NUMBER in vault.
    """
```

The call connects the user's phone (TWILIO_FROM_NUMBER or a configured personal number)
to the contact. The agent does not participate in the call - it initiates it and reports
the status.

If Twilio credentials are not in the vault, `initiate_call` raises `TwilioNotConfigured`
and the agent falls back to presenting the number with a `tel:` link.

---

## Sync API

`backend/contacts/api.py`

```
GET    /api/contacts                         - list contacts (search, paginate)
GET    /api/contacts/{id}                    - get contact detail
POST   /api/contacts                         - create manual contact
PUT    /api/contacts/{id}                    - update contact
DELETE /api/contacts/{id}                    - delete contact

GET    /api/contacts/sync/sources            - list configured sync sources
POST   /api/contacts/sync/sources            - add a CardDAV source
DELETE /api/contacts/sync/sources/{id}       - remove sync source

GET    /api/contacts/sync/google/auth        - get Google OAuth URL
GET    /api/contacts/sync/google/callback    - OAuth callback (redirect)
GET    /api/contacts/sync/microsoft/auth     - get Microsoft OAuth URL
GET    /api/contacts/sync/microsoft/callback - OAuth callback

POST   /api/contacts/sync/{source_id}/now   - trigger manual sync
GET    /api/contacts/sync/{source_id}/status - sync status and last error

POST   /api/contacts/import/vcf             - import vCard file
POST   /api/contacts/import/csv             - import CSV file

GET    /api/contacts/preferences            - get action preferences
PUT    /api/contacts/preferences            - update action preferences
```

---

## Background Sync

`backend/contacts/sync/scheduler.py`

Register a cron job (using the cron module from Prompt 15) to run delta sync for each
enabled source at its configured interval. Default: every 60 minutes.

The sync job:
1. Fetches all enabled sources from `contact_sync_sources`.
2. For each source, runs `delta_sync` if `last_full_sync_at` is set, otherwise `full_sync`.
3. Updates `last_delta_sync_at`, `contact_count`, and `last_sync_error`.
4. Emits a workspace event if new contacts were added or updated.

---

## Frontend: Contacts Page

`frontend/src/app/(workspace)/contacts/`

### Contact list (`page.tsx`)

- Search box at top (live filter as you type).
- Grouped alphabetically by family name.
- Each row: avatar (photo or initials), display name, organisation, primary email, primary phone.
- Quick actions on hover: email icon, call icon.
- Click row: opens contact detail panel.

### Contact detail panel

- Full contact info: all emails, all phones, addresses, notes.
- Source badge: "Google", "Outlook", "CardDAV", or "Manual".
- "Email" and "Call" action buttons that open the agent chat with the action pre-filled.
- Edit and delete buttons (edit disabled for externally synced contacts - must edit at source).

### Sync settings (`sync/page.tsx`)

- List of connected sources with status: last synced, contact count, error (if any).
- "Sync now" button per source.
- "Connect Google Contacts" button.
- "Connect Outlook" button.
- "Add CardDAV account" form (URL, username, password).
- "Import" button: opens file picker for `.vcf` or `.csv`.

### Action preferences (`preferences/page.tsx`)

- Toggle: "Confirm before sending emails" (default: on).
- Toggle: "Read back email drafts" (default: on).
- Toggle: "Confirm before calling" (default: on).
- Descriptive text under each toggle explaining what it controls.

---

## Output Paths

```
backend/contacts/
  __init__.py
  models.py          - SQLAlchemy models and Pydantic schemas
  tools.py           - agent tools: contact_search, contact_get, etc.
  call.py            - Twilio call initiation
  api.py             - FastAPI router
  sync/
    __init__.py
    base.py          - ContactSyncConnector ABC
    google.py        - Google People API connector
    microsoft.py     - Microsoft Graph connector
    carddav.py       - CardDAV connector
    vcf.py           - vCard file import
    csv_import.py    - CSV import with smart header mapping
    scheduler.py     - background sync cron job

frontend/src/app/(workspace)/contacts/
  page.tsx           - contact list
  [id]/page.tsx      - contact detail
  sync/page.tsx      - sync source management
  preferences/page.tsx - action preferences
```

---

## Dependencies

```
# Python (add to requirements.txt)
vobject          # vCard parsing
aiohttp          # async HTTP for CardDAV
twilio           # Twilio voice API (optional, only needed if calling is enabled)
metaphone        # phonetic name matching

# PostgreSQL extension (add to migration)
CREATE EXTENSION IF NOT EXISTS pg_trgm;
```

---

## Tests

```
tests/contacts/
  test_search.py
    - exact name match ranks first
    - phonetic match: "Jon" finds "John Smith"
    - organisation match: "Verlox" finds employees with organisation="Verlox Ltd"
    - no match returns empty list, not an error
    - disambiguation: multiple Sarahs all returned with correct ranking

  test_sync_google.py
    - full sync: mock People API response, verify contacts upserted
    - delta sync: mock syncToken response, verify only changed contacts updated
    - duplicate: same source_id updates existing record instead of creating new

  test_sync_microsoft.py
    - full sync: mock Graph response, verify contacts upserted
    - delta: mock deltaLink, verify incremental update

  test_sync_carddav.py
    - PROPFIND discovery: mock server, verify address book found
    - vCard parse: verify name, email, phone extracted correctly

  test_import.py
    - vcf import: single contact, multi-contact vCard
    - csv import: Google format, Outlook format, generic with column mapping
    - duplicate detection: same email already in contacts is updated, not duplicated

  test_call.py
    - Twilio configured: initiate_call called with correct number
    - Twilio not configured: raises TwilioNotConfigured

  test_preferences.py
    - confirm_before_email default true
    - preference update persists
    - agent natural language preference commands trigger correct update
```

---

## Acceptance Criteria

- `contact_search("John")` returns John Smith before Jonathan Archer (given_name weight).
- `contact_search("Jon")` returns "John Smith" (phonetic match).
- After Google OAuth flow completes, a full sync runs and contacts appear in the list.
- Delta sync on next cron cycle fetches only changed contacts.
- A vCard file with 50 contacts imports in under 5 seconds.
- CSV import from a Google Contacts export correctly maps columns without user intervention.
- "Email Marcus about the invoice" with a single Marcus in contacts: agent finds him,
  confirms name and email, drafts, reads back, waits for approval, sends on "send it".
- "Email Marcus about the invoice" with 3 Marcus contacts: agent lists all 3 and asks
  which one before proceeding.
- Setting `confirm_before_email = false`: agent searches, drafts, sends, and reports back
  without asking for confirmation.
- "Call Sarah" with Twilio configured: Twilio API called with Sarah's primary phone number.
- "Call Sarah" without Twilio: agent presents number and dialer link.
- Contacts synced from Google have `source = 'google'` and cannot be edited in keprix
  (edit is disabled with a note: "Edit this contact in Google Contacts").
- Manual contacts have `source = 'manual'` and are fully editable.
- No `shell=True` anywhere in this module.
- OAuth tokens are stored in the vault (Prompt 08), never in plaintext in the database.
- CardDAV password is stored in the vault, never in `contact_sync_sources` in plaintext.
