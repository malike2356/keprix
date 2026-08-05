---
id: 316-channel-shield-full-build
title: Channel Shield full build (Keprix self-hosted + Scout connector)
product: keprix
capability: channel-shield
status: completed
source: partner-call-email-phishing-preventative-2026-07-12
created: 2026-07-12
updated: 2026-07-12
completed: 2026-07-12
completion_note: |
  Shared core + 8 adapters + Agent OS contract (agentSafeContent/rawEvidenceRef,
  ingress/memory/outbound guards, policy labels, employee drawer, Agent OS panel).
  pytest tests/channel_shield: 26 passed. CLI doctor/e2e matrix present.
  Key paths: src/keprix/channel_shield/, frontend/.../channel-shield/,
  docs/features/channel-shield.md.
depends_on:
  - src/keprix/email/
  - src/keprix/channels/
  - Scout connector (optional, first-class when enabled)
  - Playbook / agent OS
tags:
  - channel-shield
  - email
  - slack
  - teams
  - telegram
  - whatsapp
  - discord
  - sms
  - web
  - sandbox
  - scout
  - self-hosted
validation:
  - Shared core + every mandatory adapter E2E
  - Scout signals when configured
  - pytest for core + each adapter
---

# 316: Channel Shield Full Build (Keprix)

## Mission

Build **Channel Shield** for Keprix: one self-hosted inbound protection plane shared across channels.

Operators protect email domains, Slack workspaces, Teams tenants, Telegram bots, WhatsApp numbers, Discord guilds, SMS numbers, and web embeds with the **same** core. The second protected surface is Keprix itself: AI Agent OS sessions, assistants, employee agents, skills, playbooks, tools, vault access, and connected workspaces must never receive untrusted raw channel content until Channel Shield has made it safe.

intercept -> immutable store -> analyse -> verdict -> deliver | quarantine + safe summary -> optional Scout.

Email is adapter one, not the whole product. Every adapter below is mandatory.

**Sibling commercial prompt (do not copy Carina code):**
`/opt/lampp/htdocs/verlox/carina/01-devends/prompts-library/pending/channel-shield/channel-shield--full-build.md`

---

## Non-negotiables

1. Read `PRODUCT_POSITIONING.md` and `keprix/BRAND-BOUNDARY.md`. Never "Carina Keprix". Never Aiva upsell inside Keprix. Scout connector optional and full-price.
2. No em dashes, no en dashes, no emojis.
3. Extend `src/keprix/email/` and `src/keprix/channels/`. One shield core, many adapters.
4. Existing email inbox/draft/send and channel messaging must keep working.
5. Fail closed default for shield protections on `malicious` and analysis `error`.
6. No new Stripe catalog prices for this feature.
7. Agent OS is a protected consumer, not a scanner. No assistant, employee agent, skill, playbook, tool, or memory writer may receive raw suspicious content before Channel Shield normalises, redacts, and classifies it.
8. Do not build offensive tooling. Tests use inert fixtures only; never include working malware, credential theft code, exploit chains, or live phishing kits.

---

## Working directories

| Area | Path |
| --- | --- |
| Email | `/opt/lampp/htdocs/verlox/keprix/src/keprix/email/` |
| Channels | `src/keprix/channels/` |
| API | `src/keprix/api/` |
| Frontend | `/opt/lampp/htdocs/verlox/keprix/frontend/` |
| Scout | existing scout signal/command modules |
| Docs | `docs/` |
| Tests | `tests/` |

---

## Read before coding

- `email/routes.py`, `store.py`, `pollers.py`, `ai_pipeline.py`, `crypto.py`
- `channels/channel_requirements.py`, `channel_probes.py`, messaging gateway paths
- Scout docs/CLI: quarantine, sandbox, suspend
- `docs/security/architecture.md`, `docs/reference/api.md`

---

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

### Canonical envelope

Same fields as Carina sibling (`channel`, `protectionId`, `externalMessageId`, `conversationId`, `from`/`to`, `text`, `links`, `attachments[]`, `rawStorageUri`, `authSignals`, `metadata`). Core verdict logic is channel-agnostic.

### Adapter interface

Each adapter: `authenticate_ingress`, `ingest`, `deliver`, `notify_safe_summary`, optional `suppress_original`, `health`. Registry-driven.

---

## Work package 01: Shared core

### Storage

- `channel_shield_protections`
- `channel_shield_messages`
- `channel_shield_attachments`
- `channel_shield_events`

Encrypt raw payloads. Config under `email_shield` **and** rename/alias to `channel_shield` in `keprix.yaml` (accept both keys during transition).

### Services + APIs

`/api/channel-shield/...` (alias `/api/email-shield/...` -> channel=email):

- protections CRUD + verify
- messages list/detail/report
- release / destroy
- adapters health

Admin-only for destroy and malicious release.

---

## Work package 02: Pipeline

Package `src/keprix/channel_shield/` (or `email/shield/` promoted to shared):

A parse/validate, B identity, C URL intel, D ClamAV/YARA, E agent triage (redacted), F Docker/sandbox + optional CAPEv2 HTTP client, G verdict + policy kernel.

Safe summary generator (channel-aware length limits).

### Agent-safe content contract

The pipeline must produce two explicit outputs:

- `rawEvidenceRef`: encrypted evidence handle for security review only.
- `agentSafeContent`: redacted, normalised, policy-labelled content safe for assistants, employee agents, skills, playbooks, memory, and UI previews.

Rules:

- Raw inbound content, attachments, URLs, HTML, headers, OCR, transcript text, and sandbox logs stay behind evidence ACLs.
- Agents receive only `agentSafeContent`, verdict, confidence, reasons, hashes, domains, attachment metadata, and allowed next actions.
- Strip or neutralise prompt injection strings, hidden instructions, tool-call bait, credential requests, exfiltration attempts, callback URLs, tracking pixels, macro hints, and encoded command fragments before any LLM sees the content.
- Never write malicious raw text into long-term memory. Store a safe summary and evidence handle instead.
- Tool execution must be blocked for `malicious`, `suspicious`, `analysis_error`, and `unknown_sender_high_risk` unless a human security approver releases the item.
- Release does not mean trust forever. Released items still carry provenance, source channel, hashes, and policy labels into downstream agent context.

---

## Work package 03: Scout connector

When Scout configured: emit accept/verdict/sandbox/quarantine/deliver/release/destroy with `channel` field; honour suspend/quarantine/sandbox commands; register product in multi-product helpers if present.

When Scout absent: local policy only. Gateway must run without Scout.

---

## Work package 04: Email adapter (full)

Modes (all required): SMTP MX / subdomain, Google/Microsoft provider feed, shadow mailbox poll.

- Production SMTP receiver (no open relay; TLS; size/rate limits; persist-before-accept).
- MIME -> envelope; SPF/DKIM/DMARC in `authSignals`.
- Deliver via SMTP smart host or provider APIs already used by `email/`.
- DNS verify in doctor + API.
- E2E: clean deliver; EICAR/YARA hold + safe summary.

Reuse `src/keprix/email/` heavily; do not fork a second mail stack.

---

## Work package 05: Slack adapter (full)

- Slack Events API + signing secret verification.
- Protection key: team_id + optional channel allowlist.
- Download files to immutable store before analysis.
- Intercept-bot architecture documented and implemented (honest about what Slack allows).
- On hold: safe summary in-thread and/or security channel; do not re-share malicious files.
- Install manifest + scopes in docs.
- Fixture E2E: message event, file_shared event.

Wire through `channels/` requirements + probes (`slack` already exists).

---

## Work package 06: Microsoft Teams adapter (full)

- Bot Framework activity webhook and/or Graph subscriptions.
- Protection key: tenant_id + team/channel.
- Graph attachment download to store.
- Safe summary via bot message to thread or security mailbox channel.
- Admin consent + app registration docs.
- Fixture E2E for text + file.

---

## Work package 07: Telegram adapter (full)

- Extend existing Telegram webhook/long-poll path.
- Protection key: bot + optional chat_id allowlist / org map.
- Media (photo/document/video) downloaded to store; never forward malicious media.
- Safe summary as plain text (Telegram limits).
- Fixture E2E using sample Update JSON.

---

## Work package 08: WhatsApp adapter (full)

- WhatsApp Cloud API primary; baileys path if enabled in tree.
- Protection key: phone_number_id / WABA id.
- Media via provider download URLs into store.
- Safe summary within WhatsApp template/session rules; document constraints.
- Fixture E2E for text + image.

Use existing `whatsapp` / `whatsapp_cloud` channel requirement ids.

---

## Work package 09: Discord adapter (full)

- Gateway or interaction webhook as already patterned in channels.
- Protection key: guild_id + channel allowlist.
- Attachment download; quarantine path.
- Safe summary in-channel or DM to configured mod role users.
- Fixture E2E.

---

## Work package 10: SMS adapter (full)

- Twilio-compatible inbound webhook (or existing provider in repo).
- Protection key: inbound number.
- MMS media to store.
- Safe summary SMS (truncated) + deep link to UI.
- Signature validation; fixture E2E.

---

## Work package 11: Web chat adapter (full)

- Inbound from web widget / embed / API chat ingress already in product.
- Protection key: site origin or embed public key.
- File uploads to store.
- In-widget system message for safe summary.
- CORS/origin checks; fixture E2E.

---

## Work package 12: Agent OS / skills / playbooks

- Skill pack `channel-shield`: triage, list quarantine, explain report, channel-aware tips.
- Playbook template **Inbound Channel Shield** with `channel` parameter and per-adapter setup nodes.
- Tool risk: release/destroy = high / approval required.
- Persona docs for WARDEN/CISO: runbook links only (no Carina branding).
- Add an Agent OS ingress guard that all assistant and employee-agent channel triggers must call before constructing prompts, memories, tool calls, tasks, or outbound replies.
- Add policy labels for `clean`, `safe_summary_only`, `needs_human_review`, `blocked`, and `destroyed`.
- Add an employee-agent escalation flow: when an assistant is asked to act on a shielded item, it must show the verdict, safe summary, allowed actions, and approval requirement before using tools or replying externally.
- Add memory protection: suspicious and malicious items can create incident memories only, never ordinary knowledge memories, client memories, or skill training examples.
- Add outbound reply guard: agents must not quote malicious payloads, forward suspicious attachments, open quarantined links, or send remediation instructions that expose dangerous content.
- Add per-agent policy controls: which assistants can view safe summaries, request release, release after approval, destroy, notify recipients, or contact external senders.

---

## Work package 13: Frontend (full)

- Primary nav: **Channel Shield**.
- Protections board grouped by channel; add wizard per adapter.
- Unified quarantine inbox with channel chips/filters.
- Message report: envelope summary, stage timeline, hashes, Scout ids.
- Settings: fail-closed, notify targets, auto-release suspects, sandbox type list.
- Adapter health panel (SMTP, webhooks, probes).
- Mobile-usable quarantine list (Agent OS empty/error/skeleton patterns).
- Agent OS panel: show which assistants and employee agents are protected, recent blocked agent triggers, approval requests, and memory writes prevented by Channel Shield.
- Employee action drawer: verdict, safe summary, evidence access state, allowed actions, approval state, and audit trail before an agent can respond or use tools.

---

## Work package 14: Docs, packaging, CLI

- `docs/features/channel-shield.md`: architecture, envelope, each adapter onboarding, E2E matrix, Scout optional.
- Update `docs/reference/api.md` and `docs/security/architecture.md`.
- Docker compose examples: SMTP port, clamav, sandbox runner, public webhook URL notes.
- CLI:
  - `keprix channel-shield doctor`
  - `keprix channel-shield adapters`
  - `keprix channel-shield e2e --channel email` (and other channels)
- Aliases: `email-shield` subcommands redirect to channel-shield for compatibility.

### Env / config sketch (`.env.example` + `keprix.yaml`)

```yaml
channel_shield:
  enabled: false
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

Accept legacy `email_shield:` key as alias during migration.

---

## Work package 15: Tests and E2E matrix

### pytest

- Core: envelope validation, verdict matrix, fail-closed, redaction, authz.
- Per adapter: ingest fixture -> pipeline (mocked sandbox) -> deliver or quarantine assertions.
- Scout: signal emit + command honour mocks.
- Agent OS: raw payload never reaches prompt builder, memory writer, skill runner, employee-agent trigger, or outbound reply tool on suspicious/malicious/error verdicts.
- Approval: release/destroy/tool execution paths require the configured role and emit audit events.
- Redaction: prompt injection, hidden HTML text, encoded commands, credential bait, suspicious URLs, and attachment names are neutralised in `agentSafeContent`.

### E2E matrix (document results in completion note)

| Adapter | Clean | Hold malicious/file | Safe summary | Scout (if configured) |
| --- | --- | --- | --- | --- |
| email | required | required | required | required |
| slack | required | required | required | required |
| teams | required | required | required | required |
| telegram | required | required | required | required |
| whatsapp | required | required | required | required |
| discord | required | required | required | required |
| sms | required | required | required | required |
| web | required | required | required | required |

Regressions: existing email routes + channel probes green.

---

## Implementation order

1. WP01 core
2. WP02 pipeline + WP03 Scout
3. WP04 email (proves core)
4. WP05-WP11 adapters (parallelise only after email green; all must merge)
5. WP12 skills/playbooks
6. WP13 UI
7. WP14 docs/CLI
8. WP15 matrix

---

## Acceptance criteria (all required)

- [ ] Shared envelope + core used by all adapters
- [ ] All eight adapters complete
- [ ] No live malicious payload delivery on any channel
- [ ] No raw suspicious or malicious content reaches Agent OS assistants, employee agents, memory, skills, playbooks, or tool calls
- [ ] Unified quarantine UI with channel filter
- [ ] Agent OS protection panel and employee action drawer complete
- [ ] Scout optional but complete when enabled
- [ ] Doctor + e2e CLI cover adapters
- [ ] Docs complete; no Carina branding
- [ ] No em/en dashes or emojis
- [ ] pytest green; matrix executed

---

## Out of scope

- Carina/Aiva managed cloud shield (sibling prompt)
- Staffed IR
- Requiring Scout for basic gateway
- Voice dial receptionist (SMS yes; voice no)

---

## Archive

Move to `../prompts-archive/316-channel-shield-full-build.md`. Mark README queue COMPLETED with date, key paths, and matrix evidence.


---

## Completion note (2026-07-12)

**Status:** COMPLETED

**Key paths:**
- `src/keprix/channel_shield/` (core, pipeline, adapters, routes, SMTP, doctor)
- `migrations/versions/020_channel_shield.py`
- `frontend/src/app/(workspace)/channel-shield/page.tsx`
- `docs/features/channel-shield.md`
- `skills/security/channel-shield/SKILL.md`
- CLI: `keprix channel-shield doctor|adapters|e2e`

**Matrix evidence:** `pytest tests/channel_shield -q` (all eight adapters clean deliver + malicious quarantine + safe summary).

