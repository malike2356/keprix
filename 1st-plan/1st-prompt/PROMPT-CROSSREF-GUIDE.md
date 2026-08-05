# Keprix Prompt Cross-Reference Guide

Use this when editing prompt bodies. Filename number is execution order. If body
text disagrees with the filename number, the filename wins.

## Authoritative Locations

| Location | Meaning |
| --- | --- |
| `pending-prompts/` | Build queue: numbered implementation prompts ready to execute. |
| `prompts-archive/` | Flat archive: completed prompts, `ref-*` architecture maps, `myapi-*`, `superseded-*`, verification records, and blueprint copies. |
| `00a-product-vision-and-agent-consolidation-map.md` | Product vision and boundary map. |
| `00b-full-build-scope-and-build-order.md` | Full build-order control document. |
| `prompts-archive/moved-to-petraclus/` | Cyber-only prompts moved out of Keprix core (if present). |

## Common Reference Numbers

| Capability | Prompt |
| --- | --- |
| Project setup and architecture | 00 |
| Full build scope and order | 00b |
| Memory and RAG | 06 |
| Vault and credentials | 08 |
| Durable playbook runtime | 51 |
| Crews and flows | 52 |
| Browser action engine | 53 |
| Data analytics code workspace | 54 |
| Self-coding patch trajectories | 55 |
| Tool library adapter pack | 56 |
| Agent evals and trace observability | 57 |
| Multi-agent messaging and studio | 58 |
| Opportunity Engine architecture | 84 |
| NEXUS persona base and registry | 96 |
| UI foundation and theme setup | 116 |
| Agent conversation workspace | 136 |
| Chat mutation E2E wiring outline (reference) | 138 |
| Chat mutation bridge and tool inventory | 139 (archived) |
| Gap detector LLM and demo patterns | 140 (archived) |
| Mutation approve, generic retry, chat follow-up | 141 (archived) |
| Gateway Web UI NDJSON stream bridge | 142 (archived) |
| Agent loop mutation hook on tool miss | 143 (archived) |
| LLM usage analytics wiring outline (reference) | 144 |
| LLM usage persistence and instrumentation | 145 (archived) |
| LLM usage analytics API | 146 (archived) |
| LLM usage workspace dashboard | 147 (archived) |
| LLM usage admin analytics and budgets | 148 (archived) |
| Mutation engine architecture reference | 149 |
| Tool synthesis engine (synthesizer, sandbox, schema, persistence) | 150 |
| Gap-to-synthesis pipeline (wiring, approval gate, API) | 151 |
| Prompt and persona mutation (DB store, write-back, evolution) | 152 |
| Scoped self-coding mutation (governed branch, test gate, merge) | 153 |
| Mutation quality and compounding (scoring, pruning, divergence) | 154 |
| Mutation governance UI (dashboard, approve/reject, rollback) | 155 |
| Workspace billing and subscription UI | 156 (archived) |
| Keprix upgrade system (CLI, migrations, rollback) | 270 (archived) |
| Cross-product upgrade (discovery, lockfile, adoption) | 272 (archived) |
| Upgrade alerts, notifier, API, and GUI | 274 (archived) |
| Layered system prompt architecture | 289 (archived) |
| Persona prompt engineering | 290 (archived) |
| Provider-agnostic tool calling | 291 (archived) |
| Changelog automation architecture (reference) | 163 |
| Conventional commits enforcement | 164 (archived) |
| git-cliff changelog generation | 165 (archived) |
| release-please release workflow | 166 (archived) |
| Skeleton loading architecture (reference) | 167 |
| Skeleton loading primitives | 168 (archived) |
| Workspace page skeleton migration | 169 (archived) |
| Admin skeleton normalization + CI contract | 170 (archived) |
| Productivity Notion/Trello architecture (reference) | 171 |
| Productivity MCP catalog + manifests | 172 |
| Productivity OAuth connect + Vault UX | 173 |
| Notion RAG source connector | 174 |
| Productivity skills + routing + playbook | 175 |
| Productivity docs + evals + verification | 176 |
| Agent Apps product architecture (reference) | 177 |
| Agent Apps frictionless hub UI | 178 (archived) |
| Agent Apps manifest v2 + dynamic forms | 179 (archived) |
| Agent Apps LLM execution bridge | 180 (archived) |
| Agent Apps install lifecycle | 181 |
| Agent Apps marketplace catalog | 182 |
| Agent Apps schedule + webhooks + API | 183 |
| Agent Apps billing + entitlements | 184 |
| Agent Apps observability + evals UI | 185 |
| Agent Apps docs + scaffold + e2e | 186 |
| Agent Apps baseline (ADK-style engine) | 67 (archived) |

## Changelog automation series (163-166)

| Prompt | Role |
| --- | --- |
| 163 | Architecture reference; tool boundaries (git-cliff vs release-please) |
| 164 | commitlint, PR title CI, contributor docs (archived) |
| 165 | `cliff.toml`, `changelog-preview.sh`, parser tests, CI preview artifact (archived) |
| 166 | release-please PRs, tag + GitHub Release, simplify `release.yml` (archived) |

Operator doc: `docs/operations/changelog-automation.md`. Series **163-166** complete.

## Skeleton loading series (167-170)

| Prompt | Role |
| --- | --- |
| 167 | Architecture reference; skeleton vs spinner decision rules; page audit |
| 168 | `components/ui/loading/*` primitives, `AsyncView`, shared UI upgrades (archived) |
| 169 | Workspace, settings, billing route migration (archived) |
| 170 | Admin normalization, `test_loading_contract.py`, docs, CI guard |

Operator doc: `docs/frontend/loading-states.md`. UI.UX pattern:
`/opt/lampp/htdocs/verlox/UI.UX/patterns/skeleton-loading-states.md`. Series **167-170** complete.

## Productivity integrations series (171-176)

| Prompt | Role |
| --- | --- |
| 171 | Architecture reference; MCP vs RAG vs skills for Notion and Trello |
| 172 | Browse catalog + `optional-mcps/` manifests for notion, notion-token, trello |
| 173 | OAuth Connect button, connection status chips, Vault-backed catalog credentials |
| 174 | `NotionSourceConnector`, `/api/rag-pipeline/ingest/notion`, pipeline UI cross-link |
| 175 | `trello` skill, `productivity-integrations` routing skill, example playbook |
| 176 | `docs/integrations/productivity-notion-trello.md`, evals, agent brief |

Operator doc: `docs/integrations/productivity-notion-trello.md` (after 176).
Build order: **172 -> 173**; **174** and **175** after 172 (parallel OK); **176** last.
Depends on autonomous MCP pack **158-161** and configurable MCP routing (shipped).

## Agent Apps product series (177-186)

| Prompt | Role |
| --- | --- |
| 177 | Architecture reference; frictionless UX, manifest v2, billing, integrations map |
| 178 | Hub UI: app picker, detail route, empty states, nav link |
| 179 | Manifest v2: typed inputs/outputs, dynamic run forms |
| 180 | Agent execution bridge: `runtime: agent`, vault readiness, permissions |
| 181 | Install lifecycle: zip upload, uninstall, upgrade, registry v2 |
| 182 | Marketplace catalog: 3 sellable templates, one-click install |
| 183 | Schedule + webhooks + public API; cron admin cross-link |
| 184 | Billing gates, usage metering, upgrade UX, pricing copy |
| 185 | Persistent run history, agent-runtime filter, evals tab |
| 186 | `docs/features/agent-apps.md`, CLI scaffold, evals, agent brief |

Baseline engine: prompt **67** (`src/keprix/agent_apps/`). Operator doc: `docs/features/agent-apps.md` (after 186).
Build order: **178 -> 179 -> 180**; **181** after **178** (parallel with 179/180 OK); **182** after **181** + **180**; **183** after **180**; **184** after **182** + **183**; **185** after **180**; **186** last.

## Web voice input series (187-192)

Mic push-to-talk in workspace chat. Reference: `prompts-archive/ref-187-web-voice-architecture.md`. Operator doc: `docs/features/web-voice-input.md`.

| Prompt | Role |
| --- | --- |
| 187 | Architecture reference; MUI + shadcn island decision (reference) |
| 188 | Shared `POST /api/audio/transcribe` on main API :3333 (archived) |
| 189 | Tailwind island + `AIVoiceInput` component (archived) |
| 190 | `useWebVoiceRecorder` + `audio-api.ts` (archived) |
| 191 | `ChatInputBar` integration (archived) |
| 192 | Settings status, rate limits, E2E, archive series (archived) |

Build order: **188** then **189** and **190** (189/190 parallel after 188), then **191**, then **192**.

## Billing UI (156); complete

Depends on archived Prompt **78** (`src/keprix/billing/`, `/api/billing/portal/*`).
Delivers signed-in `/settings/billing` wired to checkout, trials, invoices, seats.
Distinct from LLM usage (`/usage`, Prompts 145-148).

## LLM Usage Analytics Series (144-148); complete

| Prompt | Role |
| --- | --- |
| 144 | Reference outline only; do not archive |
| 145 | Durable `llm_usage_events` + recorder at all LLM call sites (archived) |
| 146 | `/api/usage/*` aggregation, budget, CSV export (archived) |
| 147 | Workspace `/usage` dashboard (archived) |
| 148 | Admin `/dashboard/usage`, overview stat card, budget alerts (archived) |

Enable with `KEPRIX_LLM_USAGE_ENABLED=true`. Reference map: `prompts-archive/ref-144-llm-usage-analytics-wiring-outline.md`.

## Mutation Engine Series (149-155); pending

| Prompt | Role |
| --- | --- |
| 149 | Architecture reference and schema; do not archive |
| 150 | `tool_synthesizer.py`, `tool_sandbox.py`, `schema_inference.py`, `MutationStore` (tool methods), DB migration, startup wiring |
| 151 | `mutation/hook.py`, wire gap detector to synthesizer, operator approval gate, `/api/mutation/tools/*` and CLI |
| 152 | `mutation/prompt_store.py`, `PersonaMutationStore`, prompt improver write-back, agent loop wired to DB prompts, `/api/mutation/prompts/*` |
| 153 | `mutation/self_coding_scope.py`, `mutation/self_coding_harness.py`, branch/merge/rollback, `/api/mutation/code/*` |
| 154 | `mutation/quality.py`, `mutation/pruner.py`, `mutation/compounding.py`, cron prune job, admin stat card, quality wiring at tool dispatch and run completion |
| 155 | Full operator dashboard at `/dashboard/mutation`, all tabs, diff viewer, approval UI, quality charts, nav badge, admin overview card |

Enable Tier 1-2 with `KEPRIX_MUTATION_ENABLED=true KEPRIX_MUTATION_TOOL_SYNTHESIS=true KEPRIX_MUTATION_PROMPT_EVOLUTION=true`.
Enable Tier 3 (operator opt-in only): `KEPRIX_MUTATION_SELF_CODING=true`.
Reference map: `prompts-archive/ref-149-mutation-engine-architecture-reference.md`.

## Chat Mutation E2E Series (138-143); complete

| Prompt | Role |
| --- | --- |
| 138 | Reference outline only; do not archive |
| 139 | Wire `run_cycle` into `/chat` stream (archived) |
| 140 | Gap detection for demo + LLM classifier (archived) |
| 141 | Approve installs tool and retries in thread (archived) |
| 142 | Unify web chat with gateway agent stream (archived) |
| 143 | Tool-miss hook in agent loop (archived) |

Sidecar bridge off by default (`KEPRIX_CHAT_MUTATION_SIDECAR=false`).

## Built apps navigation series (223-228)

Two-layer workspace nav: collapsible platform sidebar + in-content app shell. Reference: `prompts-archive/ref-223-built-apps-navigation-architecture-reference.md`.

| Prompt | Role |
| --- | --- |
| 223 | Architecture reference; manifest schema; route convention (reference) |
| 224 | Collapsible platform sidebar groups (archived) |
| 225 | `BuiltAppLayout` component kit (inner section nav, archived) |
| 226 | Built apps registry, API, UI contract `installed_apps` (archived) |
| 227 | `/apps/[slug]` route host + starter sample (archived) |
| 228 | Docs, tests, archive series (archived) |

Build order complete. Operator doc: `docs/features/built-apps-navigation.md`.

## Working Directory

All implementation prompts target:

```text
/opt/lampp/htdocs/verlox/keprix/keprix/
```

Marketing prompts target:

```text
/opt/lampp/htdocs/verlox/keprix/marketing/sites/keprix/
```

Reference agents live under:

```text
/opt/lampp/htdocs/verlox/keprix/planning/agents-to-adopt/
```
