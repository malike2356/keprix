# Channel Shield

Shared inbound protection plane for Keprix. One core pipeline; eight channel adapters.

## Architecture

```text
Adapters: email | slack | teams | telegram | whatsapp | discord | sms | web
                 \
                  v
           ShieldEnvelope (canonical)
                  |
                  v
      Channel Shield core (store, pipeline, verdict,
      quarantine, safe summary, Scout bridge)
                  |
       deliver / hold+summary / destroy
```

Messages and media are persisted (encrypted) before analysis. Fail-closed default for `malicious` and analysis `error`.

## Persistence

Runtime store is durable by default:

- Postgres when `KEPRIX_DATABASE_URL` / session factory is available (Alembic `020` + `021`)
- else SQLite at `$KEPRIX_DATA_DIR/channel_shield.db` (or `CHANNEL_SHIELD_SQLITE_PATH`)
- set `CHANNEL_SHIELD_STORE=memory` for tests / ephemeral runs

Protections, messages, attachments, and events survive process restart.

## Canonical envelope

Fields: `channel`, `protectionId`, `externalMessageId`, `conversationId`, `from`/`to`, `text`, `links`, `attachments[]`, `rawStorageUri`, `authSignals`, `metadata`.

## Pipeline stages

A parse/validate, B identity/auth signals, C URL intel, D AV/YARA heuristics (ClamAV/YARA optional), E agent triage (redacted heuristics), F sandbox for risky extensions, G verdict + policy.

## Adapters

| Channel | Protection key examples | Ingress |
| --- | --- | --- |
| email | domain or mailbox | SMTP (default port 2525), provider feed, shadow poll |
| slack | team_id | Events API webhook (`/api/channel-shield/webhooks/slack`) |
| teams | tenant_id | Bot Framework activity webhook |
| telegram | bot/chat allowlist key | Telegram webhook |
| whatsapp | phone_number_id / WABA | Cloud API webhook |
| discord | guild_id | Interaction/gateway payload webhook |
| sms | inbound number | Twilio-compatible form webhook |
| web | origin or embed public key | Widget/API ingest |

**Slack honesty:** Slack is not MX-style intercept. The adapter verifies signatures, analyses files before re-share, and posts safe summaries in-thread or to a security channel. It cannot silently rewrite peer messages.

## API

- `/api/channel-shield/...` primary
- `/api/email-shield/...` alias (email channel)

Endpoints: protections CRUD + verify, messages list/detail/report, release, destroy (admin), adapters health, ingest, per-channel webhooks.

## Scout (optional)

When Scout is configured and `channel_shield.scout.emit_signals` is true, events emit with a `channel` field. Commands (suspend/quarantine/sandbox) can be honoured locally. Gateway runs without Scout.

## Config

Home `~/.keprix/config.yaml` (accepts legacy `email_shield:` alias):

```yaml
channel_shield:
  enabled: true
  fail_closed_default: true
  smtp:
    host: 0.0.0.0
    port: 2525
  clamav_socket: null
  yara_rules_dir: null
  sandbox_required_for: [exe, dll, scr, iso, js, vbs, wsf, hta, lnk]
  adapters:
    email: true
    slack: true
    teams: true
    telegram: true
    whatsapp: true
    discord: true
    sms: true
    web: true
  scout:
    emit_signals: true
    honour_commands: true
```

Env: `CHANNEL_SHIELD_ENABLED`, `CHANNEL_SHIELD_SMTP_HOST`, `CHANNEL_SHIELD_SMTP_PORT`, `CHANNEL_SHIELD_CLAMAV_SOCKET`, `CHANNEL_SHIELD_YARA_RULES_DIR`, `CHANNEL_SHIELD_WEB_ORIGINS`, `CHANNEL_SHIELD_WEB_EMBED_KEY`.

## CLI

```bash
keprix channel-shield doctor
keprix channel-shield adapters
keprix channel-shield e2e --channel email
keprix channel-shield e2e --channel all
keprix email-shield doctor   # alias
```

## UI

Workspace nav: **Channel Shield** (`/channel-shield`). Protections board, quarantine inbox with channel filters, message report, adapter health, add-protection wizard, Agent OS protection panel, and employee action drawer (verdict, safe summary, evidence ACL, allowed actions, approval, audit).

## Agent OS contract

Pipeline outputs two explicit fields:

- `rawEvidenceRef`: encrypted evidence handle for security review only.
- `agentSafeContent`: redacted, normalised, policy-labelled content for assistants, employee agents, skills, playbooks, memory, and UI previews.

Policy labels: `clean`, `safe_summary_only`, `needs_human_review`, `blocked`, `destroyed`.

Guards (`keprix.channel_shield.agent_ingress`):

- Ingress before prompts, tools, skills, playbooks, tasks.
- Memory: suspicious/malicious create incident memories only.
- Outbound: no quoting malicious payloads, forwarding quarantined attachments, or opening held links.
- Release/destroy tools require approval (`risk: high`).

API:

- `POST /api/channel-shield/agent/guard`
- `GET /api/channel-shield/agent/os`
- `GET /api/channel-shield/messages/{id}/employee-action`
- `POST /api/channel-shield/agent/approvals`

## E2E matrix

| Adapter | Clean deliver | Hold malicious/file | Safe summary | Scout (if configured) |
| --- | --- | --- | --- | --- |
| email | required | required | required | optional |
| slack | required | required | required | optional |
| teams | required | required | required | optional |
| telegram | required | required | required | optional |
| whatsapp | required | required | required | optional |
| discord | required | required | required | optional |
| sms | required | required | required | optional |
| web | required | required | required | optional |

Run: `pytest tests/channel_shield -q` and `keprix channel-shield e2e --channel all`.

Evidence (2026-07-12): `pytest tests/channel_shield -q` -> 26 passed (core, adapters, agent OS, redaction, approval paths). Fixture E2E matrix via `run_e2e_matrix` in doctor.

## Docker notes

Expose SMTP port (2525), public HTTPS for webhooks, optional ClamAV socket, optional sandbox runner. Encrypt raw blobs with `ENCRYPTION_KEY`. Compose sketch:

```yaml
# channel-shield sidecar notes (wire into your stack)
# - keprix-api: CHANNEL_SHIELD_ENABLED=1, CHANNEL_SHIELD_SMTP_PORT=2525
# - clamav: unix socket or TCP; set CHANNEL_SHIELD_CLAMAV_SOCKET
# - public URL for /api/channel-shield/webhooks/{channel}
```

## Branding

Keprix self-hosted Channel Shield. No Carina / Aiva branding in this product surface.
