# Standalone lead outreach operations (Prompt 628)

**Status:** REAL for Community Edition local CRM + Soft Wall outreach  
**Series:** `keprix-standalone-lead-outreach`

Keprix standalone lead/outreach does not require Carina, Aiva, or Propreneur at runtime. Optional providers and enrichment APIs need their own credentials; missing keys yield honest `not_configured` / `BLOCKED_OPTIONAL_CREDENTIALS` states and must not break local CRM, import, export, or synthetic E2E.

## Setup matrix

| Mode | Persistence | Notes |
| --- | --- | --- |
| Community Edition CLI / API | SQLite (`crm.sqlite`, `outreach.sqlite`) | Default local |
| Docker Compose | Postgres + Redis via `docker/docker-compose.yml` | Set `POSTGRES_PASSWORD`, `REDIS_PASSWORD` |
| Hosted multi-user | PostgreSQL (`KEPRIX_CRM_BACKEND=auto`) | Workspace isolation enforced |
| Contabo app | Compose `deploy/contabo/docker-compose.app.yml` | Keep `KEPRIX_OUTREACH_DRY_RUN=1` unless owner flips live send |

### Local Docker

```bash
cd /opt/lampp/htdocs/verlox/keprix
cp .env.example .env   # if needed; never commit secrets
docker compose -f docker/docker-compose.yml up -d --build
curl -fsS http://127.0.0.1:3333/api/health
```

Optional Mailpit (local SMTP capture for Soft Wall approve with dry-run off):

```bash
docker compose -f docker/docker-compose.yml -f docker/docker-compose.mailpit.yml up -d
# SMTP: localhost:1025  UI: http://127.0.0.1:8025
```

Point a bound email account SMTP host at `mailpit` (from containers) or `127.0.0.1:1025` (from host). Do not enable live Contabo send without owner approval.

### Providers

- SMTP via email accounts / Vault
- ESP (SendGrid, Mailgun, SES): set keys; webhooks under `/api/outreach/webhooks/{provider}`
- Default dry-run: `KEPRIX_OUTREACH_DRY_RUN=1` stamps sends without network
- Sheet IMAP ingest: `KEPRIX_SHEET_EMAIL_INGEST=0` by default

### Channels

- Telegram journey intents: REAL (`crm/telegram_funnel.py`, `channel_journey.py`)
- Slack / WhatsApp: PARTIAL adapters (need attachment bytes)

### Imports and approvals

- Spreadsheet: `keprix crm-ingest` / `/api/crm/leads/ingest` / `/crm/leads`
- Soft Wall gates enroll, live send, stage_customer_paying, funnel NBA
- Suppression always wins over enroll/send

### Scheduler and replies

- Process due: claim-lease `outreach.process_due` / cron `outreach-process-due`
- Mailbox: `outreach.scan_replies` / cron `outreach-scan-replies`
- Observability: `GET /api/outreach/observability` or `keprix crm-funnel observability --workspace-id <ws>`

### Backup and recovery

- SQLite CE: copy workspace data dir while services stopped
- Postgres: standard `pg_dump` / restore; re-run CRM migrate (`keprix crm-migrate`) if schema lags
- After restore: verify Soft Wall pending queue, mailbox cursors, and `/api/outreach/observability`

## E2E proof

```bash
cd /opt/lampp/htdocs/verlox/keprix
./.venv/bin/python -m pytest tests/crm/test_standalone_outreach_e2e_journey.py tests/crm/test_standalone_outreach_conformance.py -q
```

Synthetic leads live in `tests/crm/fixtures/seo_lead_tracker_synthetic.csv`. Never commit private workbooks.

## Self-knowledge

After doc changes:

```bash
keprix memory index-self
# or POST /api/self-knowledge/ingest
```

Indexed paths include this file and the standalone architecture set.
