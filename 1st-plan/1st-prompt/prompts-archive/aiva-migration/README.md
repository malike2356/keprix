# Keprix + Aiva Engine Migration -- Full Prompt Map

**Status:** COMPLETED 2026-08-07 (Keprix K01-K06 + Carina C01-C05 archived)
**Date:** 2026-08-06
**Goal:** Switch Aiva's agent engine from Carina PHP to Keprix, port 4 key Aiva features to Keprix, integrate Scout protection, and wire Carina OPS backend.

## Architecture

```
User -> Aiva (PHP, KEEP)
         -> Billing, tenants, UI (KEEP)
         -> Agent Engine -> Keprix sidecar (NEW)
                             -> Outreach automation (Keprix cron)
                             -> Worker knowledge base (Keprix pgvector)
                             -> Analytics (Keprix OpenTelemetry)
                             -> Human VA escalation (Keprix subagents)
                             -> Scout protection (Keprix Warden sensors)

Scout -> monitors -> Keprix (NEW)
Carina OPS -> manages -> Keprix (NEW)
```

## Prompt Map

### Phase 1: Foundation (Build First)

| # | Prompt | Location | Status | What It Builds |
|---|---|---|---|---|
| K01 | Agent contract | Keprix | COMPLETED 2026-08-07 (archived) | POST /carina/agent/run endpoint on Keprix |
| C01 | PHP proxy | Carina | COMPLETED 2026-08-07 (archived) | Replace CarinaService.php agent loop with Keprix call |
| C02 | Tool HTTP endpoints | Carina | COMPLETED 2026-08-07 (archived) | Expose registry tools as HTTP endpoints Keprix can call |
| C03 | Engine switch mechanism | Carina | COMPLETED 2026-08-07 (archived) | Config-driven switch with rollback to original engine |

### Phase 2: Feature Porting

| # | Prompt | Location | Status | What It Builds |
|---|---|---|---|---|
| K02 | Outreach automation | Keprix | COMPLETED 2026-08-07 (archived) | Sequences, campaigns, leads, pipeline on Keprix cron |
| K03 | Worker knowledge base | Keprix | COMPLETED 2026-08-07 (archived) | pgvector-backed KB with RAG retrieval |
| K04 | Analytics engine | Keprix | COMPLETED 2026-08-07 (archived) | OpenTelemetry dashboards for Aiva usage |
| K05 | Human VA escalation | Keprix | COMPLETED 2026-08-07 (archived) | Subagent delegation for escalation workflow |

### Phase 3: Security & OPS

| # | Prompt | Location | Status | What It Builds |
|---|---|---|---|---|
| K06 | Scout integration | Keprix | COMPLETED 2026-08-07 (archived) | Warden sensors, kill switch, audit logging for Keprix |
| C04 | Scout-Keprix connector | Carina/Scout | COMPLETED 2026-08-07 (archived) | Register Keprix as Scout target, dashboard integration |
| C05 | Carina OPS integration | Carina | COMPLETED 2026-08-07 (archived) | OPS backend manages Keprix health, config, deploys |

## Standalone Web UI (not sidecar-only)

K02-K06 originally assumed Aiva PHP owned the operator UI. Keprix Web now also surfaces:

| Feature | Web path |
| --- | --- |
| Analytics | `/analytics` |
| Outreach | `/outreach` |
| Escalations | `/escalations` |
| Worker KB | `/workers/kb` |
| Scout kill & sensors | `/admin/scout-ops` |

Sidecar contracts (`/carina/*`, `/keprix/kill` token auth) remain for Aiva/Scout integrations.

## Archived

| # | Archive path |
|---|---|
| K01 | `K01-agent-contract.md` (this folder) |
| K02 | `K02-outreach-automation.md` (this folder) |
| K03 | `K03-worker-knowledge-base.md` (this folder) |
| K04 | `K04-analytics-engine.md` (this folder) |
| K05 | `K05-human-va-escalation.md` (this folder) |
| C01 | `carina/01-devends/prompts-library/02-archived_prompts/archives_from_pending_prompts/keprix-carina-engine-switch/C01-php-proxy.md` |
| C02 | `carina/01-devends/prompts-library/02-archived_prompts/archives_from_pending_prompts/keprix-carina-engine-switch/C02-tool-http-endpoints.md` |
| C03 | `carina/01-devends/prompts-library/02-archived_prompts/archives_from_pending_prompts/keprix-carina-engine-switch/C03-engine-switch-mechanism.md` |
| K06 | `K06-scout-integration.md` (this folder) |
| C04 | `carina/01-devends/prompts-library/02-archived_prompts/archives_from_pending_prompts/keprix-carina-engine-switch/C04-scout-keprix-connector.md` |
| C05 | `carina/01-devends/prompts-library/02-archived_prompts/archives_from_pending_prompts/keprix-carina-engine-switch/C05-ops-backend-integration.md` |

---

## Two directories

**Keprix side:** `keprix/1st-plan/1st-prompt/prompts-archive/aiva-migration/` (this folder).
No Keprix aiva-migration prompts remain pending (K01-K06 archived).

**Carina side:** `carina/01-devends/prompts-library/02-archived_prompts/archives_from_pending_prompts/keprix-carina-engine-switch/`
No Carina keprix-carina-engine-switch prompts remain pending (C01-C05 archived).

---

## Build Order

Phase 1 (Foundation) -> Phase 2 (Features) -> Phase 3 (Security)

Migration prompt set complete on both Keprix and Carina sides.
