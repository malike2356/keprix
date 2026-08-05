# Keprix -- Comprehensive Codebase Analysis

Generated: 2026-07-12

---

## Summary

Keprix is a hard fork of Hermes Agent (Nous Research), rearchitected as a production AI agent OS with SaaS billing, multi-persona orchestration, voice infrastructure, mobile apps, browser automation, and a product extension architecture. The core agent runtime (~85% of files) remains identical to upstream. Keprix adds ~2x the codebase in product-layer features.

**Scale:** 4,160 Python files, 697 frontend files, 208 docs pages, 727 tests, 128 skills, 104 tools, 4,280 mobile files. Total: ~2.8 GB (excluding venv and graphify cache).

**Test health:** ~500 passing across all suites. Parity gate: 10/10 suites pass. Pre-existing auth fixture failures in backup/vault API tests (4 errors).

---

## Directory Structure

```
/opt/lampp/htdocs/verlox/keprix/
├── src/keprix/           # Core + product Python (4,160 files, 117 modules)
│   ├── agent/            # Agent loop, prompt builder, tool executor, transports
│   │   ├── keprix/       # Mutation engine, self-coding, gap detection
│   │   ├── layers/       # Layered prompt system (identity, budget, safety, etc.)
│   │   └── transports/   # Provider adapters (Anthropic, OpenAI, DeepSeek, etc.)
│   ├── tui/              # Python Textual TUI (82 files)
│   ├── api/              # 83 REST routes
│   ├── tools/            # 104 tools
│   ├── skills/           # 128 skill packs
│   ├── personas/         # 10 typed agent personas + NEXUS orchestrator
│   ├── security/         # 76 files: tool ACL, egress, vault, Scout, isolation
│   ├── voice/            # 37 files: Twilio, Deepgram, VAD, call pipeline
│   ├── billing/          # 44 files: Stripe, wallet, invoicing, tax
│   ├── brain/            # 21 files: graph engine, health, replay, export
│   ├── playbook/         # 42 files: canvas, studio, NL builder, YAML compiler
│   ├── providers/        # 62 files: model/provider configs
│   ├── registries/       # 6 product registries (commands, routes, tools, config, hooks)
│   ├── extensions/       # 8 files: extension lifecycle, isolation, discovery
│   ├── agent_apps/       # App runtime, catalog, scaffold, eval harness
│   ├── agent_os/         # Onboarding, milestones, glass dashboard, run ledger
│   ├── channel_shield/   # Agent ingress, policy, memory guard, redaction
│   ├── coding/           # SWE agent: preflight gates, ladder review, git workflow
│   ├── computer_use/     # Browser harness, Playwright/Selenium drivers
│   ├── configure/        # Setup services: companion, integrations, providers
│   ├── cron/             # Job scheduler
│   ├── gateway/          # Gateway server, Twilio voice handler
│   ├── nix/              # Nix packaging (renamed from Hermes)
│   ├── proxy/            # Credential proxy, Cordon bridge, rotation
│   ├── vault/            # Knowledge vault, universal provider
│   └── ...               # ~50 more modules
├── frontend/             # Next.js 15 WebUI (697 files)
├── docs/                 # 208 markdown docs pages
├── tests/                # 727 test files
├── mobile/               # 4,280 files: Android (Kotlin) + iOS (Swift) + macOS
├── 1st-plan/             # Planning: prompts, competitor research, audits
│   ├── 1st-prompt/
│   │   ├── pending-prompts/      # Clean (0 active build prompts)
│   │   └── prompts-archive/      # ~400 archived prompts
│   └── competitor-research/
│       └── 00-agents-to-adopt/   # 29 reference agent repos cloned
└── scripts/              # Build, install, test, parity-gate scripts
```

---

## Architecture: Core vs Product Boundary

Keprix enforces a strict boundary between core engine and product modules:

**Core (must not import product):**
- `keprix.agent` -- conversation loop, tool executor, prompt builder, transports
- `keprix.tui` -- Python Textual terminal UI
- `keprix.tools` -- 104 tools
- `keprix.memory` -- episodic memory, RAG, checkpointing
- `keprix.config` -- configuration management
- CLI runtime, gateway primitives, provider routing, skill loading

**Product (may import core, not vice versa):**
- `keprix.agent_os` -- onboarding, milestones, glass dashboard, run ledger
- `keprix.channel_shield` -- agent ingress, policy enforcement, memory guard
- `keprix.billing` -- Stripe, wallet, subscriptions, invoicing
- `keprix.agent_apps` -- app runtime, catalog, deployment
- `keprix.scout` -- governance, telemetry, policy signals
- Product packs, built apps, domain workflows, admin dashboards

**Enforcement:** `tests/architecture/test_core_product_boundaries.py` uses AST parsing to verify core never imports product directly. Product modules register through `registries/` (commands, routes, tools, config, hooks, prompt layers).

---

## Key Systems

### Agent Loop
- **conversation_loop.py** (4,507 lines) -- modularized from Hermes's 5,467-line monolith
- Sub-modules: turn_context, turn_finalizer, turn_retry_state, iteration_budget
- Product hooks fire after each turn and before/after tool calls (`registries/product_hooks.py`)
- Codex app-server bypass mode for delegated coding sessions
- Layered prompt assembly via `agent/layered_assembly.py`

### Layered Prompt System
10 ordered layers injected into every agent turn:
1. IDENTITY -- model, provider, version, session
2. BUDGET -- token budget, usage, remaining turns
3. SAFETY -- child safety, weapons, malicious code, medical, self-harm
4. TOOLS -- tool descriptions, guidance blocks, skills index
5. TONE -- prose style, formatting rules, refusal tone
6. MEMORY -- memory continuity layer
7. EXECUTION -- code execution rules, ponytail ladder
8. DOMAIN -- context-specific (medical, legal, code, property)
9. PERSONA -- persona-specific prompt injection
10. PRODUCT -- product module layers (registered, opt-out per layer)

### TUI (Terminal UI)
Python Textual framework, 82 files. 116 tests pass. Feature parity with Hermes TUI at 92% (46/50 features).

- **Core engine:** Gateway WebSocket client, terminal capabilities detection, platform detection, focus management, viewport tracking, cursor tracking, mouse handling, raw mode, hit testing, alternate screen, graceful exit
- **Streaming:** Token-by-token markdown, thinking block display with spinner, tool call progress badges
- **Input:** Multi-line with 10K-entry persistent history, slash commands (30+), fuzzy matching, backend fallthrough
- **Chrome:** Top bar (session title, model badge, token counter), status bar (connection, agent state)
- **Panels:** Todo, prompts, sessions, details, agents overlay, skills hub, plugins hub, model picker, help overlay, queued messages, message metadata
- **Message display:** Virtual history with 10K+ message support, search, scroll anchoring
- **Terminal:** Window title, bell notifications, resize handling, OSC 52 clipboard, external editor
- **Utilities:** Unicode width, FPS monitor, memory monitor, render budget, debug overlay, log viewer, error boundary, external CLI, live progress, input metrics

### Tools
104 tools across categories: browser, coding, computer_use, cron, delegation, file, image_gen, MCP, memory, messaging, payments, research, security, terminal, voice, video, web_search, workspace. Tool ACL enforces per-product access control. Credential proxy (Cordon pattern) isolates secrets per request.

### Personas
10 typed agent personas + NEXUS orchestrator with routing guide enforcement:
- NEXUS -- orchestrator, task routing, multi-domain decomposition
- FORGE -- full-stack development, architecture, deployment
- CODEX -- code review, refactoring, bug fixes
- WARDEN -- security audits, hardening, compliance
- SAGE -- research, information synthesis, knowledge curation
- BEACON -- marketing campaigns, content creation, client delivery
- PRISM -- SEO, organic growth, content strategy
- COMPASS -- strategy, business decisions, prioritization
- EMBER -- wellbeing coaching, habits, personal development
- ECHO -- scheduling, admin, phone receptionist, voice

### Voice Infrastructure
37 files. Full phone receptionist pipeline: Twilio inbound webhook → Deepgram STT → Agent response → TTS → Twilio outbound. Features: VAD (voice activity detection), interruption handling, caller context resolution, escalation rules, cost tracking, phone number provisioning, wake word detection.

### Billing
44 files. Stripe integration: product/pricing catalog, checkout sessions, webhook dispatch, subscription management, invoicing, tax calculation. AI credit wallet with budget enforcement. Admin pricing dashboard. Feature gates per plan tier.

### Security
76 files. Defense-in-depth across: tool ACL (per-product, per-action), network egress policy, file gates, terminal sandbox, credential vault (encryption at rest), credential proxy (Cordon pattern with per-request injection and rotation), Scout integration (telemetry, governance, policy signals), operator policy, product isolation (query filters, middleware, verifiers), memory content scanner, pentest specification, secret scanning, rate limiting, prompt guard.

### Brain Graph
21 files. Memory graph visualization: Graphiti bridge (entity extraction), health scoring, session replay, force-directed layout, export (CSV, JSON, Obsidian), share links, activation bus, node flagging. Frontend has dedicated brain visualization pages.

### Playbooks
42 files. Visual workflow builder: canvas compiler/decompiler, expression sandbox, NL builder (natural language → workflow), YAML compiler, studio (drag-and-drop editor), template catalog, variable context, version store, workflow coach, N8N canvas importer.

### Coding Agent (SWE)
30 files. Autonomous coding: chat loop, preflight gates (diff budget, duplicate task detection), ladder review/audit/debt (ponytail integration), git workflow, filemap, parsers, patcher, scoped replace, trajectory tracking, voice-to-code.

### Self-Improvement (Mutation Engine)
Self-coding pipeline: gap detector, synthesizer, tool synthesizer, self-coding harness, quality scoring, compounding, mutation pruner, startup hooks. Generates code proposals from gap analysis, validates against the ponytail ladder, and presents to user for approval.

### Agent OS
Onboarding engine (interview agent, progress tracking, milestone system), glass dashboard (unified view of agent state), action board (task management), run ledger (persistent run tracking), level-up service (skill progression), maturity audit (four C's framework), workflow audit (session pattern analysis → skill proposals), shortcut registry, headless skill execution.

### Agent Apps
App runtime: catalog, scaffold generator, deployment bundler, eval harness, entitlements, local runner, web runner, public routes, run store, trace viewer. Built-app shell for custom agent interfaces.

### Channel Shield
Agent ingress protection: agent policy enforcement, agent-safe content filtering, memory guard (PII scrubbing), sensitive content redaction, SMTP receiver, Scout bridge (signal forwarding), durable message delivery, channel configuration service.

### Research Workspace
Obsidian vault adapter, notebook bridge (Jupyter/NotebookLM), Zotero integration, project management, citations, evidence tracking, datasets, PSPP statistics, deep research pipeline.

### Mobile Apps
4,280 files. Android (Kotlin, Gradle), iOS (Swift, Xcode), macOS daemon. Features: wake-word detection, push notifications, voice input, session management. Includes Swabble (iOS testing framework).

### Nix Packaging
12 Nix files (renamed from Hermes). keprix-agent.nix, packages.nix, devShell.nix, checks.nix, plus supporting nix files for Python, TUI, web, desktop, overlays, NixOS modules, config merge script. No flake.nix yet.

### Documentation
208 markdown pages. Architecture docs: core-product boundary, Hermes-to-keprix rename inventory, TUI freeze and parity, Hermes agent parity inventory, Keprix agent parity report, upstream adoption policy, solidness report. Feature docs: agent runtime, billing, brain, built-apps, channel shield, coding, connectors, cron, credentials, evals, feature flags, hub, LLM usage, memory, migration, playbooks, self-coding, tools, TUI, voice, workspace. Integration docs: Google Workspace, Notion, Scout, N8N, AI service accounts. Security docs: architecture, credential proxy, hardening, vault, tool credential isolation, vault migration. Operations docs: admin dashboard, backup, readiness.

### Testing
727 test files, ~500 passing. Key suites: TUI (116), agent (83), security (231), architecture (2), migration (32), parity (34), billing (44), tools (262), API (150+). Parity gate script (`scripts/check-agent-parity.sh`) runs 10 suites.

### Planning Infrastructure
~400 archived build prompts spanning 19 prompt sets (core setup, security, personas, tools, mutation, Agent OS, billing, extensions, Scout, voice, renaming, parity, TUI, and more). 29 competitor reference agent repos cloned. Comprehensive architecture analysis maintained.

---

## Hermes Parity Status

Keprix core agent runtime is ~85% identical to Hermes Agent. All 17 parity areas classified:

- 85 areas: **Same** -- identical logic, renamed identifiers only
- 21 areas: **Keprix better** -- layered prompts, domain layers, memory edit gate, connector router, mutation engine, ladder mode, voice, billing, Channel Shield, Agent OS, Agent Apps, product hook system, product prompt layers, persona system
- 2 areas: **Hermes better** (minor) -- TUI gateway recovery prompts, more Chinese-platform adapters
- 0 areas: **Missing**
- 6 areas: **Different by design** -- TUI framework (Python Textual vs TypeScript Ink), gateway architecture (Channel Shield vs monolith), desktop app, visual identity, product architecture
- 4 areas: **Blocked by product boundary** -- gateway session management owned by Channel Shield

Keprix preserves upstream attribution where required (license, documentation, upstream tracking modules). Hermes compatibility paths: legacy `.hermes` state directory readable, `HERMES_*` env vars accepted as fallback.

---

## Build Prompts Status

- **pending-prompts/**: Clean (0 active prompts). All work complete.
- **prompts-archive/**: ~400 archived prompts across completed build phases.
- **Major recent completions:** Parity suite (317-335), TUI parity (336-340), layered prompts (289), persona engineering (290), provider-agnostic tool calling (291), agent routing guide (292), ponytail ladder (249), universal vault (248), structured memory (245-247).

---

## Current Gaps

| Area | Status |
|---|---|
| TUI details panel | Missing (not blocking -- TUI otherwise feature-complete) |
| TUI resize handler | Missing (minor -- Textual handles basic resize) |
| TUI debug overlay + external link | Missing |
| Nix flake.nix | Not built (Nix files are shelfware) |
| WeChat/DingTalk adapters | Hermes has them, keprix doesn't (market-specific) |
| Production users | Zero (pre-launch) |
| Release automation | Manual releases only |
| Community presence | None (not public) |
| CI/CD | Basic test runs, no automated releases |
