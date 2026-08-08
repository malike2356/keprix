# Pending build prompts

This directory is the **execution queue**: numbered implementation prompts that are
ready to build next.

## Current status

**Current execution order (parallel OK):**

0. **Keprix Universal Sidecar public integration API** PENDING. Folder:
   `keprix-universal-sidecar/`. Product-neutral configuration and pairing for any
   self-hosted project; private sidecar port/profile, typed capability nodes,
   allowlisted project API reads/actions, durable jobs/events, signed callbacks,
   SSE, memory/retention, Python/TypeScript SDKs, starter kits, operator UI,
   Docker/Kubernetes/air-gap deployment, conformance and public GitHub release.
   Reuses `keprix-sidecar-foundation/` and the shared security contract; no second
   runtime or unrestricted tool/HTTP proxy.
1. **Keprix product sidecar readiness** PENDING. Shared contract:
   `ref-keprix-product-sidecar-contract.md`. Shared foundation queue:
   `keprix-sidecar-foundation/` (pack registry, HTTP/node API, product connectors,
   identity/grants, provisioning, events/jobs, isolation and conformance). Separate
   product build queues:
   - `keprix-sidecar-carina-aiva/` (**516-531 / CAS**): COMPLETED 2026-08-08.
     Archived at `../prompts-archive/keprix-sidecar-carina-aiva/`. Sign-off
     `docs/architecture/carina-aiva-keprix-sidecar-signoff.md`.
   - `keprix-sidecar-petraclus/`: authorised security targets, air-gap,
     edition gates, findings, remediation proposals and reports.
   - ~~`keprix-sidecar-abbis/`~~ COMPLETED 2026-08-08 (archived under `../prompts-archive/keprix-sidecar-abbis/`). Pack: `domain-packs/abbis/`. Sign-off: `docs/architecture/abbis-sidecar.md`.
     isolation, Ghana localisation, field channels and offline resilience.
   - `keprix-sidecar-xeclone/`: consent-governed persona and multimodal clone,
     Carina bridge, dual-run, biometric assets, publishing and Scout governance.
   - `keprix-sidecar-fleetz/`: bounded telemetry and fuel intelligence with a
     strict product-owned vehicle-control boundary.
   - `keprix-sidecar-clinicom/`: CLS-00..04 COMPLETED 2026-08-08 (archived under
     `../prompts-archive/keprix-sidecar-clinicom/`). CLS-05 remains pending for
     owner-approved Contabo shadow/cutover. Contabo remains on Carina.
   The product packs may build in parallel after shared runtime primitives are
   accepted. Each product remains its domain data and entitlement authority.
   Carina/Aiva CAS depends on foundation (KSF) and should lead when the goal is
   platform engine replacement; Xeclone/Clinicom remain separate product cuts.
2. ~~**Operator GUI gap closeout (467-505 Must)**~~ COMPLETED 2026-08-08 and archived under `../prompts-archive/keprix-operator-gui-gap-closeout/`. Sign-off: `docs/architecture/operator-gui-gap-signoff.md`.
3. ~~**Visual agentic CRM (429-465 + 466 + 506-515)**~~ COMPLETED 2026-08-08; entire set archived under `../prompts-archive/keprix-agentic-crm-lead-gen/` (including refs). Sign-offs: `docs/architecture/agentic-crm-signoff.md`, `docs/architecture/visual-crm-signoff.md`, `docs/architecture/agentic-crm-nice-signoff.md` (all **READY**). Operator config: `/crm/settings#connections`.
4. *(prior queue clear)* DATA ops and Public GTM archived 2026-08-07.
5. ~~**DATA ops surfaces upgrade**~~ completed 2026-08-07 and archived as `../prompts-archive/data-ops-surfaces-upgrade.md` (Must P0-P4 + `/data` tabs; P5 Nice / P6 Ultimate deferred). Evidence: `pytest tests/frontend/test_data_ops_p3.py` (5 passed) plus earlier P0/P1/P2/P4 tests.
6. ~~**Public GTM + Hermes install parity (416-428)**~~ completed 2026-08-07 and archived under `../prompts-archive/416-428-*.md`. Build order: `../prompts-archive/ref-416-keprix-public-gtm-hermes-install-build-order.md`. Sign-off: `docs/architecture/public-gtm-signoff.md` (Verdict **READY** 2026-08-07 after GitHub publicize + Contabo marketing origin).
7. ~~**Capability mesh (389-402)**~~ completed 2026-08-04 and archived under `../prompts-archive/389-402-*.md`. Build order: `../prompts-archive/ref-389-keprix-capability-mesh-build-order.md`. Graph + DoD/audit + Telegram pilot tools (viCal/calendar/contacts) + slash + IDs + discovery; evidence `pytest tests/capability_mesh tests/vical` (36 passed).
8. ~~**viCal booking adoption (376-388)**~~ completed 2026-08-04 and archived under `../prompts-archive/376-388-*.md`. Build order: `../prompts-archive/ref-376-keprix-vical-booking-build-order.md`. Code: `keprix/src/keprix/vical/`, hub `/vical`, guest `/book/{slug}`; evidence `pytest tests/vical tests/personas/test_echo_scheduler.py` (24 passed).

Completed and archived on 2026-08-07:

- **DATA ops surfaces upgrade**: Must P0-P4 + unified `/data?tab=` workspace; P3 RAG Must (MUI panel, step timeline, file/vault/URL sources, stores run counts); P5 Nice / P6 Ultimate deferred (owner ask only). Archive: `../prompts-archive/data-ops-surfaces-upgrade.md`. Evidence: `pytest tests/frontend/test_data_ops_p3.py` (5 passed).
- **Public GTM + Hermes install parity 416-428**: quarantine, public git hygiene, curl installer, PyPI honesty, install-first README/docs, `keprixai.com` metadata, MkDocs/env, ship gate, Contabo origin runbook + live marketing origin, sign-off **READY**. Archive: `../prompts-archive/416-428-*.md`. Build order: `../prompts-archive/ref-416-keprix-public-gtm-hermes-install-build-order.md`.
- **Keprix close Carina parity gaps 403-415**: multi-tenancy, isolation, governance/DSAR, AI security beyond 372, Scout Warden, packs, product tools, RAG admin, self-knowledge, billing promo/BYOK, workflows, CI. Gap doc restored with 2026-08-04 + 2026-08-07 status maps. Archive: `../prompts-archive/403-415-*.md`. Build order: `../prompts-archive/ref-403-keprix-carina-parity-build-order.md`.

Completed and archived on 2026-08-04:

- **Capability mesh 389-402**: capability graph, soft DoD, gap audit, tool exposure recipe, shared object IDs, agent discovery, Telegram pilot tools, slash/outbound hook, UI related links, rollup notes, channel parity, cutover.
- **viCal booking adoption 376-388**: domain/store, slots, lifecycle, public book, host hub, ECHO unify, ICS/reminders/webhooks, conferencing hooks, intake, deposit scaffold, cutover docs.

Completed and archived on 2026-08-03:

- LLM threat-model hardening **372-375**: fail-closed prompt guard, least-privilege ACL, RAG/Graphiti poison, Rule of Two + honest health. Build order: `../prompts-archive/ref-372-llm-threat-model-hardening-build-order.md`.

**371 Memory / Brain world-class** completed 2026-08-02 and archived:
`../prompts-archive/371-memory-world-class-roadmap.md`.

**Private OSS ship-ready pack 365-370** completed 2026-07-27 and archived. Build order:
`../prompts-archive/ref-365-private-oss-ship-ready-build-order.md`. Evidence:
frontend `tsc` green; competitor baggage quarantined; TUI parity 100/100;
TUI surpass + agent parity 10/10; `tests/api` 86 passed; private ship gate
script green; ops docs restored; sign-off at
`docs/architecture/private-ship-signoff.md`.

**gstack core + personas (360-364)** completed 2026-07-19 and archived. Built preamble loader, trigger engine, gbrain SQLite memory, sprint flow, Scout safety commands, `KeprixSkills` orchestrator, and all 11 persona SKILL.md files (NEXUS through SCOUT). Evidence: `python -m pytest tests/skills/test_preamble_loader.py tests/skills/test_trigger_engine.py tests/memory/test_gbrain.py tests/skills/test_sprint_flow.py tests/skills/test_scout_commands.py tests/skills/test_integration.py tests/skills/test_full_integration.py -q` (96 passed).

**Keprix TUI Command Center (350-360)** completed 2026-07-13 and archived. Build-order reference archived as `../prompts-archive/ref-350-keprix-tui-command-center-build-order.md`. Note: TUI prompt 360 (`360-tui-keyboard-polish-and-final-proof.md`) is distinct from gstack prompt 360.

**TUI keyboard polish and final proof (360)** completed 2026-07-13 and archived as `../prompts-archive/360-tui-keyboard-polish-and-final-proof.md`. Added the final keyboard model (`Ctrl+P`, `Ctrl+Space`, `Ctrl+L`, `Ctrl+S`, `Ctrl+M`, `Ctrl+R`, `Ctrl+K`, `?`, `Esc`), help discoverability, final Command Center proof group, docs update, and surpass script coverage. Evidence: `python -m pytest tests/tui/test_keyboard_model.py tests/tui/test_command_center_final_contract.py tests/tui/test_command_center_surpass_proof.py -q` (11 passed), `python -m pytest tests/tui -q` (295 passed), `bash scripts/check-tui-surpass-hermes.sh` passed.

**TUI empty, loading, and error states (359)** completed 2026-07-13 and archived as `../prompts-archive/359-tui-empty-loading-error-states.md`. Added shared state catalog for all required normal and error states, reusable StateView, HTTP status to state mapping, terminal-size guidance, safer network error copy, and action-id validation against the command registry. Evidence: `python -m pytest tests/tui/test_tui_state_views.py tests/tui/test_tui_error_copy.py tests/tui/test_tui_loading_states.py -q` (8 passed), `python -m pytest tests/tui -q` (284 passed), `bash scripts/check-tui-surpass-hermes.sh` passed.

**TUI review mode (358)** completed 2026-07-13 and archived as `../prompts-archive/358-tui-review-mode.md`. Added last-turn review report model, review screen with copy support, runtime review fields, stream event recording hooks, `Ctrl+R` review keybinding, and command palette review action while keeping reconnect on `Ctrl+Shift+R`. Evidence: `python -m pytest tests/tui/test_review_mode_model.py tests/tui/test_review_mode_partial_data.py tests/tui/test_review_mode_copy.py -q` (4 passed), `python -m pytest tests/tui -q` (276 passed), `bash scripts/check-tui-surpass-hermes.sh` passed.

**TUI useful status bar (357)** completed 2026-07-13 and archived as `../prompts-archive/357-tui-useful-status-bar.md`. Added stable operational status snapshots, fixed-width rendering, health/offline clarity, transport/session/queue/busy/tokens/latency/cost/voice segments, and app wiring from runtime state. Evidence: `python -m pytest tests/tui/test_status_bar_segments.py tests/tui/test_status_bar_width.py tests/tui/test_status_bar_offline.py -q` (4 passed), `python -m pytest tests/tui -q` (272 passed), `bash scripts/check-tui-surpass-hermes.sh` passed.

**TUI theme system (356)** completed 2026-07-13 and archived as `../prompts-archive/356-tui-theme-system.md`. Added exactly three persisted themes, deterministic contrast checks, renderer theme tokens, Textual theme classes, command palette theme actions, and local `/theme` switching. Evidence: `python -m pytest tests/tui/test_theme_system.py tests/tui/test_theme_contrast.py tests/tui/test_theme_persistence.py -q` (8 passed), `python -m pytest tests/tui -q` (268 passed), `bash scripts/check-tui-surpass-hermes.sh` passed.

**TUI session map (355)** completed 2026-07-13 and archived as `../prompts-archive/355-tui-session-map.md`. Added session relationship metadata, compact session map model, sidebar widget, keyboard navigation model, and flat fallback for existing APIs. Evidence: `python -m pytest tests/tui/test_session_map_model.py tests/tui/test_session_map_navigation.py tests/tui/test_session_map_fallback.py -q` (7 passed), `python -m pytest tests/tui -q` (260 passed), `bash scripts/check-tui-surpass-hermes.sh` passed.

**TUI inline tool cards (354)** completed 2026-07-13 and archived as `../prompts-archive/354-tui-inline-tool-cards.md`. Added pure inline tool card renderer, redaction, expandable state, ToolCard widget, and message renderer integration while preserving old compact tool summary compatibility. Evidence: `python -m pytest tests/tui/test_tool_cards_renderer.py tests/tui/test_tool_cards_redaction.py tests/tui/test_tool_cards_expand_collapse.py -q` (8 passed), `python -m pytest tests/tui -q` (253 passed), `bash scripts/check-tui-surpass-hermes.sh` passed.

**TUI live runtime timeline (353)** completed 2026-07-13 and archived as `../prompts-archive/353-tui-live-runtime-timeline.md`. Added runtime timeline model, widget, runtime store event recording, and app integration for turns, transport, streaming, tools, subagents, approvals, clarify events, usage, queue, interrupts, and errors. Evidence: `python -m pytest tests/tui/test_runtime_timeline.py tests/tui/test_runtime_timeline_volume.py -q` (5 passed), `python -m pytest tests/tui -q` (245 passed), `bash scripts/check-tui-surpass-hermes.sh` passed.

**TUI workspace cockpit first screen (352)** completed 2026-07-13 and archived as `../prompts-archive/352-tui-workspace-cockpit-first-screen.md`. Added a pure cockpit state/render model, Textual workspace cockpit widget, and app integration for empty transcript and offline first-screen context. Evidence: `python -m pytest tests/tui/test_workspace_cockpit.py tests/tui/test_workspace_cockpit_offline.py -q` (6 passed), `python -m pytest tests/tui -q` (240 passed), `bash scripts/check-tui-surpass-hermes.sh` passed.

**TUI command palette (351)** completed 2026-07-13 and archived as `../prompts-archive/351-tui-command-palette.md`. Added command palette model, overlay, app keybindings, and action dispatch for slash commands, sessions, models, runtime actions, help, files, skills, and plugins. Evidence: `python -m pytest tests/tui/test_command_palette_model.py tests/tui/test_command_palette_widget.py tests/tui/test_command_palette_actions.py -q` (10 passed), `python -m pytest tests/tui -q` (234 passed), `bash scripts/check-tui-surpass-hermes.sh` passed.

**TUI Command Center foundation (350)** completed 2026-07-13 and archived as `../prompts-archive/350-tui-command-center-foundation.md`. Added pure Command Center action, registry, state, layout, telemetry, and contract models. Evidence: `python -m pytest tests/tui/test_command_center_foundation.py tests/tui/test_command_center_contracts.py -q` (9 passed), `python -m pytest tests/tui -q` (224 passed), `bash scripts/check-tui-surpass-hermes.sh` passed.

**TUI surpass Hermes (345-349)** completed 2026-07-13 and archived. Build-order reference archived as `../prompts-archive/ref-345-tui-surpass-hermes-build-order.md`.

**TUI superiority proof harness (349)** completed 2026-07-13 and archived as `../prompts-archive/349-tui-superiority-proof-harness.md`. Added `src/keprix/tui/surpass_contract.py`, `tests/tui/test_tui_surpass_contract.py`, `docs/architecture/tui-surpass-hermes-contract.md`, and `scripts/check-tui-surpass-hermes.sh`. Evidence: `bash scripts/check-tui-surpass-hermes.sh` passed with `TUI parity contracts: 100/100 passed` and `TUI surpass contracts: passed`; `python -m pytest tests/tui -q` (215 passed).

**TUI performance and battle hardening (348)** completed 2026-07-13 and archived as `../prompts-archive/348-tui-performance-and-battle-hardening.md`. Added hardening helpers for latency budgets, memory budgets, HTTP fault copy, safe stream JSON lines, resize coalescing, terminal minimums, and traceback-free user messages. Evidence: `python -m pytest tests/tui/test_performance_budgets.py tests/tui/test_long_session_endurance.py tests/tui/test_fault_matrix.py tests/tui/test_terminal_matrix.py tests/tui/test_overlay_recovery.py tests/tui/test_memory_budgets.py -q` (21 passed), `python -m pytest tests/tui -q` (210 passed), `bash scripts/check-tui-parity.sh` passed with `TUI parity contracts: 100/100 passed`, compile and style checks passed.

**TUI agent runtime proximity (347)** completed 2026-07-13 and archived as `../prompts-archive/347-tui-agent-runtime-proximity.md`. Added `runtime_transport` with typed events, HTTP, WebSocket, in-process, selector, errors, and app wiring through `self.transport` for runtime-covered operations. Evidence: `python -m pytest tests/tui/test_runtime_transport_contract.py tests/tui/test_runtime_transport_selector.py tests/tui/test_runtime_transport_http.py tests/tui/test_runtime_transport_websocket.py tests/tui/test_runtime_transport_in_process.py tests/tui/test_runtime_event_normalization.py tests/tui/test_runtime_interrupt_latency.py -q` (14 passed), `python -m pytest tests/tui -q` (189 passed), `bash scripts/check-tui-parity.sh` passed with `TUI parity contracts: 100/100 passed`, compile and style checks passed.

**TUI renderer superiority (346)** completed 2026-07-13 and archived as `../prompts-archive/346-tui-renderer-superiority.md`. Added deterministic renderer primitives for cells, Unicode and markup-safe measurement, dirty frame diffing, streaming markdown and code blocks, themed message grouping, search highlight plus selection, stable viewport helpers, snapshots, profiler, and CI benchmark helpers. Evidence: `python -m pytest tests/tui/test_renderer_cells.py tests/tui/test_renderer_measure.py tests/tui/test_renderer_diff.py tests/tui/test_renderer_markdown_streaming.py tests/tui/test_renderer_messages.py tests/tui/test_renderer_viewport_selection.py tests/tui/test_renderer_benchmarks.py -q` (18 passed), `python -m pytest tests/tui -q` (175 passed), `bash scripts/check-tui-parity.sh` passed with `TUI parity contracts: 100/100 passed`, compile and style checks passed.

**TUI source granularity parity (345)** completed 2026-07-13 and archived as `../prompts-archive/345-tui-source-granularity-parity.md`. Added granular `commands`, `composer`, `contracts`, `gateway`, `layout`, `overlays`, `panels`, `renderer`, `runtime`, `search`, `sessions`, and `terminal` packages with compatibility exports. Evidence: `python -m pytest tests/tui/test_granularity_contract.py tests/tui/test_import_compatibility.py tests/tui/test_renderer_contracts.py tests/tui/test_command_contracts.py tests/tui/test_runtime_contracts.py -q` (21 passed), `python -m pytest tests/tui -q` (157 passed), `bash scripts/check-tui-parity.sh` passed with `TUI parity contracts: 100/100 passed`, compile and style checks passed.

**TUI 100 percent Hermes behavior parity (341-344)** completed 2026-07-13 and archived. Prompt 341 archived as `../prompts-archive/341-tui-runtime-data-parity.md`; evidence: `python -m pytest tests/tui/test_runtime_data_parity.py -q` (3 passed), `python -m pytest tests/tui -q` (121 passed), compile and style checks passed. Prompt 342 archived as `../prompts-archive/342-tui-interaction-parity.md`; evidence: `python -m pytest tests/tui/test_slash_command_schema.py tests/tui/test_interaction_parity.py -q` (5 passed), `python -m pytest tests/tui -q` (126 passed), compile and style checks passed. Prompt 343 archived as `../prompts-archive/343-tui-reliability-parity.md`; evidence: `python -m pytest tests/tui/test_fault_injection.py -q` (4 passed), `python -m pytest tests/tui -q` (130 passed), compile and style checks passed. Prompt 344 archived as `../prompts-archive/344-tui-proof-and-contract-harness.md`; build-order reference archived as `../prompts-archive/ref-341-tui-100-percent-hermes-parity-build-order.md`. Evidence: `bash scripts/check-tui-parity.sh` passed with `TUI parity contracts: 100/100 passed`, `python -m pytest tests/tui -q` (136 passed), compile and style checks passed.

**TUI parity follow-up (336-340)** completed 2026-07-13 and archived under `../prompts-archive/336-*.md` through `../prompts-archive/340-*.md`. Verification/debug pass found the previous implementation incomplete against the prompts, then added the missing TUI parity primitives: typed gateway messages and router, mouse parsing, raw mode, hit testing, typed message envelopes, message renderer, virtual history/renderer/search, terminal title/notifications/resize/startup helpers, Unicode/emoji/bidi helpers, FPS/memory/render budget, debug/log/error helpers, external CLI/link helpers, live progress/input metrics, app layout, todo/prompts/session/details panels, agents/skills/plugins hubs, message metadata, queued messages, help overlay, fuzzy matching, slash argument parsing, expanded slash completion, 10K persistent input history, and backend-safe slash fallthrough. Runtime follow-up wired visible slash command suggestions, Up/Down slash selection, `/debug`, `/open <url>`, resize refresh, and a useful Workspace sidebar. Evidence: `python -m pytest tests/tui -q` (115 passed), prompt-requested file inventory `MISSING_COUNT=0`, style scan for forbidden dash and emoji/symbol ranges passed on touched TUI files.

**Keprix/Hermes core alignment and agent parity (317-335)** completed 2026-07-12. Archived under `../prompts-archive/317-*.md` through `../prompts-archive/335-*.md`, with references `../prompts-archive/ref-317-keprix-hermes-core-alignment-build-order.md` and `../prompts-archive/ref-327-hermes-agent-parity-build-order.md`. Verification/debug pass added missing architecture docs, corrected parity reporting, fixed the parity gate, fixed local `.env` test leakage, restored `keprix upstream --help`, and fixed the TUI slash input runtime crash. Evidence: `bash scripts/check-agent-parity.sh` (10/10 passed), `python -m pytest tests/tui -q` (102 passed), `python -m pytest tests/upstream tests/upgrade tests/cli -q` (89 passed).

**Channel Shield (316)** completed 2026-07-12. Shared inbound protection plane across email, Slack, Teams, Telegram, WhatsApp, Discord, SMS, and web, plus Agent OS ingress/memory/outbound guards (`agentSafeContent` / `rawEvidenceRef`). Archived: `../prompts-archive/316-channel-shield-full-build.md`. Key paths: `src/keprix/channel_shield/`, `docs/features/channel-shield.md`, UI `/channel-shield`, CLI `keprix channel-shield`. Evidence: `pytest tests/channel_shield -q` (26 passed); `keprix channel-shield e2e --channel all`.

**Agent OS UI polish (301-315)** completed 2026-07-12. Hub/subnav, milestones on onboarding, Ship defaults on glass, nav sync, period selector, onboard vs onboarding IA, shared Empty/Error/skeletons, breadcrumbs to glass, Memory Galaxy tabs + node click + force layout, glass tasks links, board header links, frosted panels, usage↔glass `?days=` sync, and API/feature docs. Archived under `../prompts-archive/301-*.md` through `315-*.md`. Build order: `../prompts-archive/ref-301-agent-os-ui-polish-build-order.md`.

**Open-amount coffee donation (300)** completed 2026-07-12. Footer donate sheet + `POST /api/billing/donation/checkout` `{ amount_gbp }` via Stripe `price_data` (min £1). Archived: `../prompts-archive/300-open-amount-coffee-donation.md`.

**Conversational channel config (298)** and **Wave 2 (299)** completed on Keprix; Carina port completed 2026-07-11. Archived under `../prompts-archive/`. Carina SOP: `carina/01-devends/SOP/043-conversational-configuration.md`.

**MyApi Open adoption** completed 2026-07-11 and archived under `../prompts-archive/`.


**Agent routing guide (292 OpenMontage AGENT_GUIDE pattern)** completed 2026-07-10 and archived. NEXUS/WARDEN/ECHO `AGENT_GUIDE.md`, mandatory prompt preamble, `guide_enforcer.py`. Note: distinct from archived Fable **292** skill-first.

**Fable-class product power (292-297)** completed 2026-07-10 and archived. Skill-first, deliverable paths, deferred tool search, memory continuity, connector-first, and operator-owned policy kernel. Master reference: `../prompts-archive/ref-292-fable-class-product-power-master-reference.md`. Build order: `../prompts-archive/ref-292-fable-class-product-power-build-order.md`.

**Extension architecture (267, Prompt 84 variant)** completed and archived. Entry-point discovery, compatibility checks, lifecycle, config merge, isolation, scout extension, `keprix.yaml` via upgrade manifest. Not the Chase **267-272** video ingest series.

**Brain visualization pack (257, 259, 261, 263)** completed and archived. Layout engine, health dashboard, session replay, export/share (PNG, JSON, Obsidian ZIP, CSV, password-protected read-only share links).

**Brain session replay (261)** completed and archived. Step-through replay of past sessions with activation pulses, transport bar, session picker, path highlighting, transcript/CSV export. See `brain/session_replay.py` and `/brain/graph` replay mode.

**Brain health dashboard (259)** completed and archived. Health score, orphan/stale/hub/duplicate detection, coverage gaps, bulk delete/merge/archive APIs, `/brain/health` dashboard, graph health overlay, sidebar widget. See `brain/health.py` and `tests/brain/test_brain_health.py`.

**Brain graph layout engine (257)** completed and archived. Four layout modes (force, temporal, radial, hierarchical), Louvain-lite clustering, custom minimap, incremental layout for 200+ nodes, Web Worker force sim for 100+ nodes. See `frontend/src/lib/brain/layout-registry.ts`.

**Layered prompts, tool calling, and persona engineering (289-291)** completed 2026-07-10 and archived. Fable-style layered system prompt, provider-agnostic tool schema/normaliser/audit, and engineered persona prompts for all 10 specialists.

**Built apps navigation (223-228)** completed 2026-07-09 and archived. Reference **223** remains as `../prompts-archive/ref-223-*.md`.

**KNIME adoption pack (233-238)** completed 2026-07-09 and archived. Visual Playbook Studio, Connector Catalog Marketplace, Community/Enterprise gates, Scout publish telemetry, Templates/variables/coach, and Import bridges/run overlay are shipped; see `../prompts-archive/ref-233-knime-adoption-build-order.md` and `../prompts-archive/ref-233-knime-adoption-master-reference.md`.

**Agentic OS adoption (256-265)** completed 2026-07-09 and archived. See `../prompts-archive/ref-255-agentic-os-adoption-build-order.md` and `../prompts-archive/ref-255-agentic-os-adoption-master-reference.md`. Supersedes unnumbered drafts `245-structured-workspace-memory.md`, `246-session-to-skill-automation.md`, `247-headless-skill-launcher.md`, `248-universal-vault-provider.md` (do not implement those; use 256-265).

**Chase five tools adoption (267-272)** completed 2026-07-09 and archived. Video ingest, notebook bridge, Graphiti MCP, design live preview, coding preflight, and Obsidian vault pack are shipped. See `../prompts-archive/ref-266-chase-five-tools-adoption-build-order.md`, `../prompts-archive/ref-266-chase-five-tools-adoption-master-reference.md`, and `../../competitor-research/chase-ai-five-tools-adoption.md`. Source: [IRPEfl2BD_c](https://www.youtube.com/watch?v=IRPEfl2BD_c).

**Nate Herk AIOS adoption (274-279)** completed 2026-07-09 and archived. Four C's audit, level-up, onboard interview, connections matrix, hot cache, and Google Workspace connector are shipped. See `../prompts-archive/ref-273-nate-herk-aios-adoption-build-order.md`, `../prompts-archive/ref-273-nate-herk-aios-adoption-master-reference.md`, and `../../competitor-research/nate-herk-aios-adoption.md`. Source: [bCljOfCH8Ms](https://www.youtube.com/watch?v=bCljOfCH8Ms). Amends **258**, **264**, **265**.

**ML service (229-232)** completed 2026-07-09 and archived.

**Credential proxy (239-243)** completed 2026-07-09 and archived. Local injection proxy, tool credential isolation/audit trail, hot credential rotation, Cordon skill pack, and vault migration/fallback are shipped. See `../prompts-archive/239-credential-injection-proxy.md` through `../prompts-archive/243-vault-deprecation-migration.md`, and `docs/security/credential-proxy.md`.

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

Prior series **117-212** archived under `../prompts-archive/`.

## Queue

| # | File | Status |
| --- | --- | --- |
| 360 | `../prompts-archive/360-gstack-core-infrastructure.md` | COMPLETED 2026-07-19 (archived; gstack, not TUI) |
| 361 | `../prompts-archive/361-gstack-personas-think-ship.md` | COMPLETED 2026-07-19 (archived) |
| 362 | `../prompts-archive/362-gstack-personas-plan-review-build.md` | COMPLETED 2026-07-19 (archived) |
| 363 | `../prompts-archive/363-gstack-personas-security-test-reflect.md` | COMPLETED 2026-07-19 (archived) |
| 364 | `../prompts-archive/364-gstack-personas-ops-governance-integration.md` | COMPLETED 2026-07-19 (archived) |
| 350 | `../prompts-archive/350-tui-command-center-foundation.md` | COMPLETED 2026-07-13 (archived) |
| 351 | `../prompts-archive/351-tui-command-palette.md` | COMPLETED 2026-07-13 (archived) |
| 352 | `../prompts-archive/352-tui-workspace-cockpit-first-screen.md` | COMPLETED 2026-07-13 (archived) |
| 353 | `../prompts-archive/353-tui-live-runtime-timeline.md` | COMPLETED 2026-07-13 (archived) |
| 354 | `../prompts-archive/354-tui-inline-tool-cards.md` | COMPLETED 2026-07-13 (archived) |
| 355 | `../prompts-archive/355-tui-session-map.md` | COMPLETED 2026-07-13 (archived) |
| 356 | `../prompts-archive/356-tui-theme-system.md` | COMPLETED 2026-07-13 (archived) |
| 357 | `../prompts-archive/357-tui-useful-status-bar.md` | COMPLETED 2026-07-13 (archived) |
| 358 | `../prompts-archive/358-tui-review-mode.md` | COMPLETED 2026-07-13 (archived) |
| 359 | `../prompts-archive/359-tui-empty-loading-error-states.md` | COMPLETED 2026-07-13 (archived) |
| 360 | `../prompts-archive/360-tui-keyboard-polish-and-final-proof.md` | COMPLETED 2026-07-13 (archived) |
| 345 | `../prompts-archive/345-tui-source-granularity-parity.md` | COMPLETED 2026-07-13 (archived) |
| 346 | `../prompts-archive/346-tui-renderer-superiority.md` | COMPLETED 2026-07-13 (archived) |
| 347 | `../prompts-archive/347-tui-agent-runtime-proximity.md` | COMPLETED 2026-07-13 (archived) |
| 348 | `../prompts-archive/348-tui-performance-and-battle-hardening.md` | COMPLETED 2026-07-13 (archived) |
| 349 | `../prompts-archive/349-tui-superiority-proof-harness.md` | COMPLETED 2026-07-13 (archived) |
| 341 | `../prompts-archive/341-tui-runtime-data-parity.md` | COMPLETED 2026-07-13 (archived) |
| 342 | `../prompts-archive/342-tui-interaction-parity.md` | COMPLETED 2026-07-13 (archived) |
| 343 | `../prompts-archive/343-tui-reliability-parity.md` | COMPLETED 2026-07-13 (archived) |
| 344 | `../prompts-archive/344-tui-proof-and-contract-harness.md` | COMPLETED 2026-07-13 (archived) |
| 336 | `../prompts-archive/336-tui-parity-core-engine.md` | COMPLETED 2026-07-13 (archived) |
| 337 | `../prompts-archive/337-tui-parity-streaming-input-slash.md` | COMPLETED 2026-07-13 (archived) |
| 338 | `../prompts-archive/338-tui-parity-app-chrome-panels-hubs.md` | COMPLETED 2026-07-13 (archived) |
| 339 | `../prompts-archive/339-tui-parity-message-display-history-terminal.md` | COMPLETED 2026-07-13 (archived) |
| 340 | `../prompts-archive/340-tui-parity-utility-platform-polish.md` | COMPLETED 2026-07-13 (archived) |
| 317-326 | `../prompts-archive/ref-317-keprix-hermes-core-alignment-build-order.md` | COMPLETED 2026-07-12 (archived) |
| 327-335 | `../prompts-archive/ref-327-hermes-agent-parity-build-order.md` | COMPLETED 2026-07-12 (archived) |
| 316 | `316-channel-shield-full-build.md` | COMPLETED 2026-07-12 (archived; Channel Shield full build) |
| 301-315 | `../prompts-archive/ref-301-agent-os-ui-polish-build-order.md` | COMPLETED 2026-07-12 (archived) |
| 223 | `../prompts-archive/ref-223-built-apps-navigation-architecture-reference.md` | Reference |

**Current execution order:** none active in this folder (archived rows below for history):

| File | Status |
| --- | --- |
| `../prompts-archive/data-ops-surfaces-upgrade.md` | ARCHIVED 2026-08-07 (Must P0-P4 + `/data` tabs; P5 Nice / P6 Ultimate deferred) |
| `372-fail-closed-prompt-guard-and-context-quarantine.md` | ARCHIVED 2026-08-03 |
| `373-least-privilege-tool-acl-lethal-trifecta.md` | ARCHIVED 2026-08-03 |
| `374-rag-graphiti-ingest-poison-controls.md` | ARCHIVED 2026-08-03 |
| `375-rule-of-two-human-gates-honest-health.md` | ARCHIVED 2026-08-03 |

Series map: `../prompts-archive/ref-372-llm-threat-model-hardening-build-order.md`.

**371 Memory / Brain world-class** completed 2026-08-02 and archived as `../prompts-archive/371-memory-world-class-roadmap.md`. Hub control plane, orchestrator recall, temporal KG + dreaming, eval scripts. Remaining polish (docs rewrite, Graphiti live query, NLP extract) noted in archive as non-blocking follow-ups.

Previously: gstack 360-364 and TUI Command Center queues complete.

**Chase five tools (267-272):** Series archived completed. OSS tool patterns from Chase AI video. Build order: `../prompts-archive/ref-266-chase-five-tools-adoption-build-order.md`.

**Nate Herk AIOS (274-279):** Series archived completed. Extends Agentic OS with scored maturity audit, onboard interview, connections matrix, hot cache, and Google Workspace. Build order: `../prompts-archive/ref-273-nate-herk-aios-adoption-build-order.md`. MVP demo: **276 + 274 + 277** shipped.

**KNIME adoption (233-238):** Keprix pack archived completed. Visual Studio **233**, Connector Catalog **234**, Edition gates **235**, Scout telemetry **236**, Templates/variables/coach **237**, and Import/run overlay **238** shipped. Reference: `../prompts-archive/ref-233-knime-adoption-master-reference.md`, `../prompts-archive/ref-233-knime-adoption-build-order.md`. Carina prompts remain in `carina/01-devends/prompts-library/pending/knime-adoption--*.md` (01-05).

**ML service (229-232):** Series archived completed.

**Built apps navigation (223-228):** Two-layer nav: collapsible Keprix platform sidebar + in-content `BuiltAppLayout` for products at `/apps/[slug]/*`. Reference: `../prompts-archive/ref-223-built-apps-navigation-architecture-reference.md`. Build order: `../prompts-archive/ref-223-built-apps-navigation-build-order.md`.

Series **224-228** archived completed.

**Fable-class product power (292-297):** Completed and archived. Build order `../prompts-archive/ref-292-fable-class-product-power-build-order.md`. MVP demo: **292 + 293 + 294**.

## Where other prompt files live

| Path | Purpose |
| --- | --- |
| `../prompts-archive/ref-` | Wiring outlines and architecture maps |
| `../prompts-archive/ref-233-visual-playbook-studio-architecture-reference.md` | Visual playbook canvas map |
| `../prompts-archive/ref-233-knime-adoption-build-order.md` | KNIME pack 233-235 + Carina cross-ref |
| `../prompts-archive/ref-223-built-apps-navigation-architecture-reference.md` | Built apps nav map |
| `../prompts-archive/ref-223-built-apps-navigation-build-order.md` | Prompts 223-228 order |
| `../prompts-archive/ref-266-chase-five-tools-adoption-master-reference.md` | Chase five tools map |
| `../prompts-archive/ref-266-chase-five-tools-adoption-build-order.md` | Prompts 267-272 order |
| `../prompts-archive/ref-273-nate-herk-aios-adoption-master-reference.md` | Nate Herk AIOS map |
| `../prompts-archive/ref-273-nate-herk-aios-adoption-build-order.md` | Prompts 274-279 order |
| `../prompts-archive/ref-220-tui-first-run-onboarding-architecture-reference.md` | TUI setup/onboarding map |
| `../prompts-archive/ref-292-fable-class-product-power-master-reference.md` | Fable-class product power map |
| `../prompts-archive/ref-292-fable-class-product-power-build-order.md` | Prompts 292-297 order |
| `../prompts-archive/ref-301-agent-os-ui-polish-master-reference.md` | Agent OS UI polish map (after Prompt 270) |
| `../prompts-archive/ref-301-agent-os-ui-polish-build-order.md` | Prompts 301-315 order |
| `../PROMPT-IMPLEMENTATION-AUDIT.md` | Implementation status |
| `../prompts-archive/` | Shipped prompts |

## Adding a new prompt

1. Add `NNN-short-title.md` here with acceptance criteria and dependencies.
2. Build fully (no stubs); see `../README.md` No Stubs Rule.
