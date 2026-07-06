# Control center

The control center is the admin dashboard for your Keprix instance. Access it at `/admin`. It requires the `admin` role.

## Overview

The control center provides four major areas:

| Area | What you can do |
| --- | --- |
| **Users** | Invite, edit, and deactivate users; set roles; view activity |
| **Settings** | Instance name, LLM providers, feature flags, rate limits, tool gates |
| **Infrastructure** | Container health, database stats, queue depth, storage usage |
| **Governance** | Audit log, mutation history, pack installs, Scout integration |

## Users

### Inviting a user

1. Go to **Admin > Users** (`/dashboard/users`).
2. Click **Invite user**, enter email and role (`user` or `admin`).
3. Click **Send invite**.

If SMTP is configured (`KEPRIX_SMTP_HOST`, etc.), an email is sent with an accept link.
Otherwise the UI shows a copyable invite URL.

The invitee opens `/auth/accept-invite?token=...`, sets a username and password, and is signed in.

Alternatively via API:

```http
POST /api/users/invite
{"email": "user@example.com", "role": "user", "message": "Join us"}
```

Accept invite:

```http
GET /api/auth/invites/{token}
POST /api/auth/invites/accept
{"token": "...", "password": "securepass123", "username": "jane"}
```

### Editing a user

Change role, suspend, or reactivate a user in **Admin > Users > Manage**.

API:

```http
PUT /api/users/{user_id}
{"role": "admin", "status": "active"}
```

`status` values: `active`, `suspended`, `invited`.

Delete:

```http
DELETE /api/users/{user_id}
```

### Billing seat invites

Team seat invites from `/settings/billing` use the same accept flow and provision a workspace account when the invite is accepted.

### API key management

Admins can view and revoke all API keys across users in **Admin > Users > {user} > API Keys**.

## Settings

### LLM providers

Add, edit, or remove LLM provider configurations in **Admin > Settings > LLM Providers**.

Each provider entry has:
- Provider type (Anthropic, OpenAI, Google, Ollama, custom OpenAI-compatible)
- API key (stored in the Vault)
- Default model
- Enabled/disabled toggle

The **default provider** is used for all turns unless the user or a playbook specifies otherwise.

See [LLM providers](../configuration/llm-providers.md) for the full guide.

### Feature flags

Selectively disable features per-instance:

| Flag | Effect |
| --- | --- |
| `research.enabled` | Hide the research launcher and `/research` route |
| `coding.enabled` | Hide the coding workspace |
| `mutation.enabled` | Disable the Mutation Engine entirely |
| `agent_teams.enabled` | Disable agent teams |
| `rag_pipelines.enabled` | Disable RAG pipeline UI |
| `agent_apps.enabled` | Disable agent apps runner |
| `voice.enabled` | Disable voice input/output |

Set flags in **Admin > Settings > Feature flags** or via env:

```bash
KEPRIX_FEATURE_RESEARCH=true
KEPRIX_FEATURE_MUTATION=true
KEPRIX_FEATURE_CODING=true
```

### Rate limits

```bash
KEPRIX_RATE_LIMIT_PER_USER_PER_MINUTE=30    # default: 30 messages/min per user
KEPRIX_RATE_LIMIT_TOTAL_PER_MINUTE=200      # instance-wide cap
```

Override in **Admin > Settings > Rate limits**.

### Tool gates

Configure which tools require admin approval before the agent can run them. Defaults are set per-tool in the tool manifest; the control center lets you override them.

### Pack gate

Control how community packs are installed:

- **Open**: any user can install packs.
- **Admin only**: only admins can install packs.
- **Gated**: any user can request; admin approves.

## Infrastructure

### Container health

**Admin > Infrastructure > Health** shows the status of each Docker container with restart history and memory/CPU usage.

### Database stats

Shows PostgreSQL table sizes, slow queries (from `pg_stat_statements`), and last backup time.

### Queue depth

Shows the number of pending jobs in each Redis queue (agent tasks, research jobs, indexing jobs, notification jobs).

### Storage usage

Total storage used per component: PostgreSQL, ChromaDB, uploaded files, mutation tools, logs.

## Governance

### Audit log

**Admin > Governance > Audit log** shows a searchable, filterable view of the `audit_log` table. Filter by user, event type, date range, or resource.

Export to CSV: click **Export** in the filter bar.

### Mutation history

**Admin > Governance > Mutations** shows all proposed, approved, and rejected mutations across all users with the synthesised code, approval time, and who approved.

### Pack history

**Admin > Governance > Packs** shows all pack installs and uninstalls with the pack manifest, installer, and install time.

### Scout export

When Scout integration is configured, governance events are forwarded automatically. Status and error details appear in **Admin > Governance > Scout**.

See [Scout integration](../integrations/scout.md).

## Backup and restore

Schedule automated backups in **Admin > Infrastructure > Backup**:

```bash
KEPRIX_BACKUP_ENABLED=true
KEPRIX_BACKUP_SCHEDULE="0 3 * * *"   # daily at 3am
KEPRIX_BACKUP_S3_BUCKET=my-backups
KEPRIX_BACKUP_S3_PREFIX=keprix/
KEPRIX_BACKUP_RETENTION_DAYS=30
```

Manual backup:

```bash
python3 -m keprix.keprix_cli.main backup create
```

Restore from a backup:

```bash
python3 -m keprix.keprix_cli.main backup restore <backup-id>
```

## Related

- [Security architecture](../security/architecture.md)
- [Hardening](../security/hardening.md)
- [Governance](../security/governance.md)
- [Scout integration](../integrations/scout.md)
- [LLM providers](../configuration/llm-providers.md)
