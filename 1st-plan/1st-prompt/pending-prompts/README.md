# Pending build prompts

This directory is the **execution queue**: numbered implementation prompts that are
ready to build next.

## Current status

**Agent OS UI polish (301-315)** completed 2026-07-12. Hub/subnav, milestones on onboarding, Ship defaults on glass, nav sync, period selector, onboard vs onboarding IA, shared Empty/Error/skeletons, breadcrumbs to glass, Memory Galaxy tabs + node click + force layout, glass tasks links, board header links, frosted panels, usage↔glass `?days=` sync, and API/feature docs. Archived under `../prompts-archive/completed/301-*.md` through `315-*.md`. Build order: `../reference/301-agent-os-ui-polish-build-order.md`.

**Open-amount coffee donation (300)** completed 2026-07-12. Footer donate sheet + `POST /api/billing/donation/checkout` `{ amount_gbp }` via Stripe `price_data` (min £1). Archived: `../prompts-archive/completed/300-open-amount-coffee-donation.md`.

**Conversational channel config (298)** and **Wave 2 (299)** completed on Keprix; Carina port completed 2026-07-11. Archived under `../prompts-archive/completed/`. Carina SOP: `carina/01-devends/SOP/043-conversational-configuration.md`.

**MyApi Open adoption** completed 2026-07-11 and archived under `../prompts-archive/myapi-open-adoption/`.


**Agent routing guide (292 OpenMontage AGENT_GUIDE pattern)** completed 2026-07-10 and archived. NEXUS/WARDEN/ECHO `AGENT_GUIDE.md`, mandatory prompt preamble, `guide_enforcer.py`. Note: distinct from archived Fable **292** skill-first.

**Fable-class product power (292-297)** completed 2026-07-10 and archived. Skill-first, deliverable paths, deferred tool search, memory continuity, connector-first, and operator-owned policy kernel. Master reference: `../reference/292-fable-class-product-power-master-reference.md`. Build order: `../reference/292-fable-class-product-power-build-order.md`.

**Extension architecture (267, Prompt 84 variant)** completed and archived. Entry-point discovery, compatibility checks, lifecycle, config merge, isolation, scout extension, `keprix.yaml` via upgrade manifest. Not the Chase **267-272** video ingest series.

**Brain visualization pack (257, 259, 261, 263)** completed and archived. Layout engine, health dashboard, session replay, export/share (PNG, JSON, Obsidian ZIP, CSV, password-protected read-only share links).

**Brain session replay (261)** completed and archived. Step-through replay of past sessions with activation pulses, transport bar, session picker, path highlighting, transcript/CSV export. See `brain/session_replay.py` and `/brain/graph` replay mode.

**Brain health dashboard (259)** completed and archived. Health score, orphan/stale/hub/duplicate detection, coverage gaps, bulk delete/merge/archive APIs, `/brain/health` dashboard, graph health overlay, sidebar widget. See `brain/health.py` and `tests/brain/test_brain_health.py`.

**Brain graph layout engine (257)** completed and archived. Four layout modes (force, temporal, radial, hierarchical), Louvain-lite clustering, custom minimap, incremental layout for 200+ nodes, Web Worker force sim for 100+ nodes. See `frontend/src/lib/brain/layout-registry.ts`.

**Layered prompts, tool calling, and persona engineering (289-291)** completed 2026-07-10 and archived. Fable-style layered system prompt, provider-agnostic tool schema/normaliser/audit, and engineered persona prompts for all 10 specialists.

**Built apps navigation (223-228)** completed 2026-07-09 and archived. Reference **223** remains in `../reference/`.

**KNIME adoption pack (233-238)** completed 2026-07-09 and archived. Visual Playbook Studio, Connector Catalog Marketplace, Community/Enterprise gates, Scout publish telemetry, Templates/variables/coach, and Import bridges/run overlay are shipped; see `../reference/233-knime-adoption-build-order.md` and `../reference/233-knime-adoption-master-reference.md`.

**Agentic OS adoption (256-265)** completed 2026-07-09 and archived. See `../reference/255-agentic-os-adoption-build-order.md` and `../reference/255-agentic-os-adoption-master-reference.md`. Supersedes unnumbered drafts `245-structured-workspace-memory.md`, `246-session-to-skill-automation.md`, `247-headless-skill-launcher.md`, `248-universal-vault-provider.md` (do not implement those; use 256-265).

**Chase five tools adoption (267-272)** completed 2026-07-09 and archived. Video ingest, notebook bridge, Graphiti MCP, design live preview, coding preflight, and Obsidian vault pack are shipped. See `../reference/266-chase-five-tools-adoption-build-order.md`, `../reference/266-chase-five-tools-adoption-master-reference.md`, and `../../competitor-research/chase-ai-five-tools-adoption.md`. Source: [IRPEfl2BD_c](https://www.youtube.com/watch?v=IRPEfl2BD_c).

**Nate Herk AIOS adoption (274-279)** completed 2026-07-09 and archived. Four C's audit, level-up, onboard interview, connections matrix, hot cache, and Google Workspace connector are shipped. See `../reference/273-nate-herk-aios-adoption-build-order.md`, `../reference/273-nate-herk-aios-adoption-master-reference.md`, and `../../competitor-research/nate-herk-aios-adoption.md`. Source: [bCljOfCH8Ms](https://www.youtube.com/watch?v=bCljOfCH8Ms). Amends **258**, **264**, **265**.

**ML service (229-232)** completed 2026-07-09 and archived.

**Credential proxy (239-243)** completed 2026-07-09 and archived. Local injection proxy, tool credential isolation/audit trail, hot credential rotation, Cordon skill pack, and vault migration/fallback are shipped. See `../prompts-archive/completed/239-credential-injection-proxy.md` through `../prompts-archive/completed/243-vault-deprecation-migration.md`, and `docs/security/credential-proxy.md`.

**Structured workspace memory (245)** completed 2026-07-09 and archived. Covered by the Agentic OS memory implementation: workspace templates, auto-generated folder indexes, `KEPRIX.md` and `CLAUDE.md` navigation guides, memory-to-index bridge, CLI/API/template picker, docs, and tests.

**Aiva phone receptionist (244)** completed 2026-07-09 and archived. Twilio inbound voice webhook, bidirectional media stream bridge, provider-agnostic STT -> Keprix agent -> TTS pipeline, caller memory, interruption/silence handling, cost estimator, admin/session UI, Twilio provisioning UI, docs, and tests are shipped.

**Twilio inbound phone voice (246)** completed 2026-07-09 and archived. Adds `/api/voice/inbound`, `/api/voice/stream/{call_sid}`, `/api/voice/status`, Twilio signature validation, call records/finalizer, media audio helpers, streaming STT/TTS facades, phone provisioning, escalation policy, and voice call tools.

**Brain graph API (247)** completed 2026-07-09 and archived. Adds graph types, retrieval edge query engine, node resolvers with tombstones, edge co-occurrence weights, authenticated `/api/brain/graph` endpoints, neighbours/node/stats APIs, and tests.

**Session-to-skill automation (248)** completed 2026-07-09 and archived. Covered by the Agent OS skill loop: session pattern detector, skill proposal store/routes, auto-skill packaging, improvement loop, weekly review report, self-improvement settings UI, docs, and tests.

**Brain graph canvas (249)** completed 2026-07-09 and archived. Adds `/brain/graph`, React Flow canvas, graph data hook, API-to-flow transforms, kind-specific node renderers, hover highlighting/dimming, MiniMap/controls, empty/loading states, content panel shell, nav entry, and frontend transform test.

**Headless skill launcher (250)** completed 2026-07-09 and archived. Covered by Agent OS action board/headless run service, with compatibility `/api/skills/{slug}/run` and run history routes, `useSkillRunner`, docs, scheduling/shortcuts/pins/result review/run ledger, and tests.

**Brain node content panel (251)** completed 2026-07-09 and archived. Adds full node fetch panel, kind-specific content registry, first-degree connections list, back/forward panel history, inline edit shell, delete/edge cleanup, responsive drawer behavior, and tests.

**Universal vault provider (252)** completed 2026-07-09 and archived. Covered by universal markdown vault provider/API/UI/tools/docs, with `keprix vault doctor` and `migrate-workspace` CLI coverage added.

**Brain graph filter/search/focus (253)** completed 2026-07-09 and archived. Adds kind/date/session filters, URL/localStorage filter state, debounced graph search API/UI, search dimming/highlights, depth-aware focus mode, focus banner/slider, and tests.

**Ponytail ladder minimal code (254)** completed 2026-07-09 and archived. Adds bundled Ponytail coding skill/rules, ladder prompt/mode storage, mutation ladder gate, review/audit/debt/metrics helpers, API routes, dashboard, docs, nav, and tests.

**Brain live session activation (255)** completed 2026-07-09 and archived. Adds live activation emitter/bus, SSE stream, graph edge persistence, conversation tool/skill/session pulses, frontend EventSource hook, live session selector, timeline export, node/edge pulse animations, and tests.

**Resource quotas and fairness scheduler (271)** completed 2026-07-10 and archived. Adds/repairs per-product quota config/store/enforcer, shared quota runtime, fair-share scheduler, `/api/admin/quotas` dashboard API including scheduler stats, LLM preflight/slot/usage wiring, provider quota compatibility, and tests.

**Security defense-in-depth (275)** completed 2026-07-10 and archived. Adds instruction boundary hardening, output guard redaction, terminal sandbox policy, file/network gates, A2A message signing/replay checks, health response model fix, and tests.

**UI navigation architecture (276)** completed 2026-07-10 and archived. Canonical primary nav now exposes Home, Sessions, Brain, Skills, Tasks, Tools, Voice, Settings, and Admin slots; mobile bottom tabs, quota usage surfacing, `/home`/`/sessions`/`/voice`/admin aliases, and quota admin page are shipped.

**Home page shell (277)** completed 2026-07-10 and archived. `/home` now renders the launchpad shell with greeting, recent sessions, brain stats, active tasks, discovery card, empty state, canonical session links, and brain graph stats integration.

**Security gap analysis / Scout integration (278)** completed 2026-07-10 and archived. Verified existing Scout signal/listener/sync bridge plus memory content scanner and tool sequence guard local defenses.

**Hermes upstream monitor (279)** completed 2026-07-10 and archived. Upstream release inventory, adoption evaluation, prompt generation, CLI commands, and Scout release signaling are present.

**Adopt Hermes features (280)** completed 2026-07-10 and archived. Checkpoint manager compatibility, MoA, x_search, progressive tool disclosure, and Scout hardening tests are verified.

**Production deployment and Scout integration (281)** completed 2026-07-10 and archived. Production Scout helpers, deployment script, signal/command test suites, health payloads, and product registration flow are verified.

**Multi-product Scout dashboard (282)** completed 2026-07-10 and archived. Product registration, per-product policies, dashboard summary/routes, alert config, metrics, and cross-product correlation are verified.

**Incident response playbook (283)** completed 2026-07-10 and archived. Incident declarations, L3/L4 responses, vault seal, forensics, auto-response, pentest/audit/reporting, runbook, and drill coverage are verified.

**TUI first-run onboarding (220-222)** completed 2026-07-07 (archived).

**Account and security pack (214-219)** completed 2026-07-06 (archived).

Prior series **117-212** archived under `../prompts-archive/completed/`.

## Queue

| # | File | Status |
| --- | --- | --- |
| 301 | `301-agent-os-hub-subnav.md` | PENDING (start here) |
| 302 | `302-agent-os-milestones-onboarding-ui.md` | PENDING |
| 303 | `303-agent-os-ship-defaults-glass-panel.md` | PENDING |
| 304 | `304-agent-os-nav-fallback-sync.md` | PENDING |
| 305 | `305-agent-os-glass-period-selector.md` | PENDING |
| 306 | `306-agent-os-onboard-onboarding-ia.md` | PENDING |
| 307 | `307-agent-os-shared-empty-error-skeletons.md` | PENDING |
| 308 | `308-agent-os-breadcrumbs-fix.md` | PENDING |
| 309 | `309-memory-galaxy-tabs-node-click.md` | PENDING |
| 310 | `310-agent-os-glass-tasks-links.md` | PENDING |
| 311 | `311-agent-os-action-board-header-links.md` | PENDING |
| 312 | `312-agent-os-frosted-glass-treatment.md` | PENDING (nice) |
| 313 | `313-memory-galaxy-force-layout.md` | PENDING (nice) |
| 314 | `314-usage-glass-period-sync.md` | PENDING (nice) |
| 315 | `315-agent-os-api-docs-glass-milestones-phase5.md` | PENDING (nice) |
| 223 | `../reference/223-built-apps-navigation-architecture-reference.md` | Reference |

**MVP demo for 301-315:** ship **301 + 302 + 303 + 304 + 305 + 306**, then polish 307-311, then nice 312-315.

**Chase five tools (267-272):** Series archived completed. OSS tool patterns from Chase AI video. Build order: `../reference/266-chase-five-tools-adoption-build-order.md`.

**Nate Herk AIOS (274-279):** Series archived completed. Extends Agentic OS with scored maturity audit, onboard interview, connections matrix, hot cache, and Google Workspace. Build order: `../reference/273-nate-herk-aios-adoption-build-order.md`. MVP demo: **276 + 274 + 277** shipped.

**KNIME adoption (233-238):** Keprix pack archived completed. Visual Studio **233**, Connector Catalog **234**, Edition gates **235**, Scout telemetry **236**, Templates/variables/coach **237**, and Import/run overlay **238** shipped. Reference: `../reference/233-knime-adoption-master-reference.md`, `../reference/233-knime-adoption-build-order.md`. Carina prompts remain in `carina/01-devends/prompts-library/pending/knime-adoption--*.md` (01-05).

**ML service (229-232):** Series archived completed.

**Built apps navigation (223-228):** Two-layer nav: collapsible Keprix platform sidebar + in-content `BuiltAppLayout` for products at `/apps/[slug]/*`. Reference: `../reference/223-built-apps-navigation-architecture-reference.md`. Build order: `../reference/223-built-apps-navigation-build-order.md`.

Series **224-228** archived completed.

**Fable-class product power (292-297):** Completed and archived. Build order `../reference/292-fable-class-product-power-build-order.md`. MVP demo: **292 + 293 + 294**.

## Where other prompt files live

| Path | Purpose |
| --- | --- |
| `../reference/` | Wiring outlines and architecture maps |
| `../reference/233-visual-playbook-studio-architecture-reference.md` | Visual playbook canvas map |
| `../reference/233-knime-adoption-build-order.md` | KNIME pack 233-235 + Carina cross-ref |
| `../reference/223-built-apps-navigation-architecture-reference.md` | Built apps nav map |
| `../reference/223-built-apps-navigation-build-order.md` | Prompts 223-228 order |
| `../reference/266-chase-five-tools-adoption-master-reference.md` | Chase five tools map |
| `../reference/266-chase-five-tools-adoption-build-order.md` | Prompts 267-272 order |
| `../reference/273-nate-herk-aios-adoption-master-reference.md` | Nate Herk AIOS map |
| `../reference/273-nate-herk-aios-adoption-build-order.md` | Prompts 274-279 order |
| `../reference/220-tui-first-run-onboarding-architecture-reference.md` | TUI setup/onboarding map |
| `../reference/292-fable-class-product-power-master-reference.md` | Fable-class product power map |
| `../reference/292-fable-class-product-power-build-order.md` | Prompts 292-297 order |
| `../reference/301-agent-os-ui-polish-master-reference.md` | Agent OS UI polish map (after Prompt 270) |
| `../reference/301-agent-os-ui-polish-build-order.md` | Prompts 301-315 order |
| `../PROMPT-IMPLEMENTATION-AUDIT.md` | Implementation status |
| `../prompts-archive/completed/` | Shipped prompts |

## Adding a new prompt

1. Add `NNN-short-title.md` here with acceptance criteria and dependencies.
2. Build fully (no stubs); see `../README.md` No Stubs Rule.
