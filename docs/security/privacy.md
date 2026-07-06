# Privacy and data handling

Keprix is self-hosted: you control the infrastructure, the data, and who has access. This page describes what data Keprix stores, how it is handled, and how to meet GDPR and other privacy obligations.

## Data stored by Keprix

| Category | Where stored | Retention |
| --- | --- | --- |
| Conversations (messages, tool calls) | PostgreSQL `conversations` / `messages` tables | Configurable; default: forever |
| Memory documents | ChromaDB + PostgreSQL metadata | Until deleted |
| Uploaded files | Filesystem (`data/files/`) + PostgreSQL metadata | Until deleted |
| Audit log | PostgreSQL `audit_log` | Configurable; default: 2 years |
| User accounts | PostgreSQL `users` table | Until deleted |
| Sessions | Redis (TTL: `KEPRIX_SESSION_TTL`) | Expires automatically |
| API keys (hashed) | PostgreSQL | Until revoked |
| Vault secrets (encrypted) | PostgreSQL | Until deleted |

## No telemetry by default

Keprix does not phone home. No usage statistics, crash reports, or conversation data are sent to any third party unless you explicitly configure an integration (Scout, OpenTelemetry, etc.).

The only outbound network calls Keprix makes out of the box are:

- LLM provider API calls (Anthropic, OpenAI, etc.) - sends prompts and receives responses.
- SearXNG web search calls (internal container by default).
- Any external API calls made by tools (declared in tool manifests).

## Data sent to LLM providers

When the agent sends a message to an LLM provider:

- The conversation history (messages within the context window) is sent.
- Retrieved memory documents are sent as part of the prompt.
- Tool results are sent as context.

No user account data (email, name) is included in prompts unless the agent explicitly retrieves it as part of a tool call.

To avoid sending data to any external provider, use a local model via Ollama:

```bash
KEPRIX_DEFAULT_PROVIDER=ollama
KEPRIX_OLLAMA_BASE_URL=http://ollama:11434
```

See [Local models](../features/local-models.md).

## GDPR compliance

### Data subject access requests (DSAR)

Export all data for a specific user:

```bash
python3 -m keprix.keprix_cli.main gdpr export --user user@example.com --output dsar-export.zip
```

The export includes: conversations, uploaded files, memory documents attributed to the user, and account information.

Via API (admin only):

```http
POST /api/admin/gdpr/export
{"user_id": "uuid-here"}
```

### Right to erasure

Delete all data for a user:

```bash
python3 -m keprix.keprix_cli.main gdpr delete --user user@example.com
```

This:
- Deactivates and anonymises the user account (preserves the user row as `[deleted]` for audit integrity).
- Deletes all conversations and messages.
- Deletes all uploaded files.
- Removes memory documents attributed to the user.
- Removes API keys and sessions.
- Removes Vault entries owned by the user.
- Adds an erasure record to the audit log.

Via API:

```http
DELETE /api/admin/gdpr/user/{user_id}
```

### Data retention policy

Set automatic retention limits:

```bash
KEPRIX_RETENTION_CONVERSATIONS_DAYS=365   # delete conversations older than 1 year
KEPRIX_RETENTION_AUDIT_LOG_DAYS=730       # keep audit log for 2 years
KEPRIX_RETENTION_FILES_DAYS=180           # delete orphaned files after 6 months
```

Retention jobs run daily at 3am (configurable).

### Consent

Keprix does not handle consent for end users by default. If you are building a multi-tenant product on top of Keprix, implement consent collection before creating user accounts.

The audit log records the timestamp and IP of account creation, which can serve as evidence of terms acceptance if you record consent at that point.

## Encryption

### In transit

All API responses are served over HTTP by default (development). For production, terminate TLS at your reverse proxy. See [Hardening](hardening.md).

### At rest

- PostgreSQL: encrypt the disk volume at the OS/hosting level.
- ChromaDB: encrypt the volume.
- Vault secrets: encrypted with AES-256-GCM inside the database (application-level encryption, not just disk encryption).

## Personally identifiable information in conversations

Conversations may contain PII if users type it or if tools retrieve it (email contacts, calendar events, etc.).

Consider:

- Restricting retention with `KEPRIX_RETENTION_CONVERSATIONS_DAYS`.
- Enabling automatic conversation summarisation (replaces raw messages with a summary after N days, reducing PII exposure while retaining context).
- Using a local LLM to avoid sending PII to external providers.

## Multi-user isolation

Each user's conversations, memory, files, and projects are isolated at the database level (filtered by `user_id`). Admin users can view all data. There is no row-level security in PostgreSQL by default; admin-level database access bypasses application-level isolation.

For strict multi-tenant isolation, run separate Keprix instances per tenant.

## Related

- [Security architecture](architecture.md)
- [Hardening](hardening.md)
- [Governance](governance.md)
- [Control center](../features/control-center.md)
- [Local models](../features/local-models.md)
