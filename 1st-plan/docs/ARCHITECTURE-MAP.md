# Keprix Architecture Map

This document categorises the full Keprix plan using the Linux analogy:

Keprix Core is the AI agent kernel.
Keprix is the self-hosted distribution.
Keprix Hub is the package ecosystem.
Carina, Aiva, and Scout live in the separate commercial workspace.
Labyrinth Scout is an optional external governance connector.
Petraclus is a separate cybersecurity product that can use Keprix as an AI backbone.

Nothing in this map deletes or replaces the existing prompts. It explains where each group belongs so the build can proceed in a clean order.

## Layer 1: Keprix Core, The Kernel

This is the minimal runtime everything else depends on. It should stay small, stable, and strongly tested.

| Area | What Belongs Here | Prompt Group |
| --- | --- | --- |
| Agent runtime | Conversation loop, context, state, tool dispatch, streaming | `03` |
| Model routing | Provider router, fallback chains, cost tracking, model playbooks | `04` |
| Tool execution | Tool registry, terminal tools, file tools, sandbox execution, risky action approval | `05` |
| Memory | Episodic memory, RAG, pgvector, hybrid search, workspace context | `06` |
| Skills and plugins | Skill loader, plugin registry, hot reload, community pack schema | `07` |
| Credential vault | Secret storage, redaction, scoped env injection, audit log | `08`, `08b` |
| Security envelope | Input validation, output redaction, headers, rate limits, safe tool policy | `02`, `20` |
| API runtime | REST, WebSocket, OpenAPI, health, metrics, tracing | `16`, `17` |
| Durable playbook runtime | State graphs, checkpoints, interrupts, resumable execution | `64` |
| Multi-agent messages | Agent messages, group chat, agent-as-tool, MCP workbench | `71` |

Build principle: if a feature is required by many products, it belongs in the kernel. If it is a specific product experience, it belongs higher up.

## Layer 2: Keprix System Services

These are equivalent to OS services. They run in the background and power the workspace.

| Service | What It Does | Prompt Group |
| --- | --- | --- |
| Scheduler | Cron jobs, recurring tasks, trigger conditions | `13` |
| Notification service | Inbox, alerts, routing, escalation rules | `34` |
| Connector service | MCP, ACP, OAuth connectors, external integrations | `15` |
| Browser service | Playwright, Selenium, Chrome extension bridge, action logs | `66` |
| Analytics service | Code interpreter, DataFrame memory, reports, ML and stats workflows | `40`, `67` |
| Coding service | Repo filemap, issue-to-patch, scoped edits, test loop, trajectories | `36`, `37`, `68` |
| Evals service | Benchmarks, graders, traces, regression reports | `39`, `70` |
| Self-configuration | Health checks, auto-repair, dependency setup, system optimisation | `14` |
| Scout bridge client | Optional governance event bridge to Labyrinth Scout | `46` |

Build principle: services can depend on Keprix Core, but Keprix Core should not depend on services.

## Layer 3: Keprix Workspace, The Distribution Experience

This is what a self-hosted user actually installs and uses. It is the "Ubuntu" or "Fedora" layer around the kernel.

| Workspace Area | What It Gives The User | Prompt Group |
| --- | --- | --- |
| Documents and notes | File store, notes, search, summaries, workspace context | `09` |
| Calendar and tasks | Calendar sync, task manager, scheduled routines | `09`, `13` |
| Email | IMAP/SMTP, triage, drafts, thread summaries, send approvals | `10` |
| Contacts | Contacts sync, fuzzy name matching, confirmation flow | `10b` |
| Messaging | WhatsApp, Slack, Telegram, Discord, SMS, unified inbox | `11` |
| Deep research | Source ranking, citations, claim verification, research reports | `12` |
| Opportunity Engine | Market demand, pain mining, ICP, competitors, offer, assets, launch, growth | `52` to `63` |
| Localisation and voice | i18n, local language support, speech input/output | `35` |
| Support | In-app support, diagnostics, incident communication | `50` |

Build principle: the distribution should feel useful on day one, even before a user installs any extra packs.

## Layer 4: Keprix UI Surfaces

These are the desktop environment equivalents. They should all feel like the same product.

| Surface | What It Is For | Prompt Group |
| --- | --- | --- |
| Web UI | Main workspace, tools, settings, approvals, artifacts | `31`, `32` |
| CLI | Developer and operator commands | `31`, `33`, `41` |
| TUI | Terminal-native workspace and agent run monitor | `31`, `32` |
| Mobile | Native iOS and Android companion apps | `18` |
| Browser extension | Browser action approval, web page context, safe web agent control | `66` |
| Agent Studio | Visual multi-agent and playbook builder | `71` |

Build principle: the user should not feel like they changed products when moving from web UI to mobile, CLI, or browser extension.

## Layer 5: Keprix Hub, Package And App Ecosystem

This is the package manager and app store layer.

| Hub Area | What It Provides | Prompt Group |
| --- | --- | --- |
| Skill packs | Reusable behaviours and domain skills | `07`, `44` |
| Playbooks | Structured workflows and reusable process templates | `12`, `64`, `65` |
| Tool adapters | Search, scraping, RAG, databases, vector stores, media, automation, sandboxes | `69` |
| Domain packs | Legal, finance, property, health, borehole, localised industry packs | `38` |
| Templates | App templates and project starters | `37`, `44` |
| Marketplace | Pack registry, submission, install, ratings, updates | `44` |
| SDKs | Python SDK and TypeScript SDK | `19` |

Build principle: Keprix should become more valuable as the ecosystem grows, without bloating the kernel.

## Layer 6: Developer Platform

This is for people building products on top of Keprix.

| Developer Capability | What It Enables | Prompt Group |
| --- | --- | --- |
| App Foundation SDK | Build apps on top of Keprix APIs | `19` |
| OpenAI-compatible API | Drop-in backend for chat and embeddings clients | `17` |
| Project builder | Scaffold apps, manage monorepos, generate packages | `37` |
| Self-coding agent | Generate, test, and install tools after approval | `36`, `68` |
| API observability | Logs, metrics, traces, run events | `16`, `70` |
| Benchmarks | Quality gates for agent workflows | `39`, `70` |
| Documentation and community | Docs, landing page, contribution guide, release process | `42`, `43` |

Build principle: developers should be able to build an AI product on Keprix without understanding every internal service.

## Layer 7: Local Governance And Optional Trust Connectors

This cuts across all layers. Keprix includes local safety controls. Scout remains
an optional external connector. Aiva is not part of Keprix.

| Governance Area | Local Keprix | Optional External Connector | Prompt Group |
| --- | --- | --- | --- |
| Approval gates | Local approval before risky actions | Scout team policy sync when connected | `02`, `05`, `46`, `64` |
| External human review | External sign-off by named party (not a Keprix user) | Scout audit record of review decision | `86` |
| Audit logs | Local run logs and traces | Scout audit console and export | `16`, `46`, `70` |
| Kill switch | Local stop controls | Scout central kill switch | `46` |
| Prompt injection defence | Local filters and risk checks | Scout managed policy and event stream | `20`, `46` |
| Compliance exports | Local reports and PDF generation | Scout evidence packs and clinical event taxonomy | `46`, `87`, `90` |
| GDPR and data rights | Consent ledger, DSAR export, erasure, retention policy | Scout GDPR event stream | `88` |
| Legal acceptance | Policy versioning, acceptance gate, CLI gate | Scout compliance record | `89` |
| Clinical pack gate | Sign-off before new pack version activates | Scout pack change event | `91` |
| Outbound notify | SMTP and webhook dispatch to external parties | (routed via notify-external; Scout not involved) | `92` |

Not in Keprix: Aiva keys, Aiva billing, Aiva white-labeling, Aiva upsell stubs,
Scout paid evidence packs, and enterprise trust attestation.

Build principle: Keprix must be safe locally, and external trust services must be
explicit connectors that users choose to configure.

## Layer 8: Separated Products

These are not all inside Keprix. They explain the product boundaries.

| Product | Layer | Relationship To Keprix |
| --- | --- | --- |
| Keprix | Self-hosted distribution | Open-source entry point and builder platform |
| Petraclus | Cybersecurity product | **First consumer**; bundles Keprix; see `keprix-projects/petraclus/` |
| AbbiS | Borehole industry SaaS | **Second consumer**; SDK + domain packs on Keprix; see `keprix-projects/abbis/` |
| Fleetz | Fleet tracking SaaS | Planned Keprix consumer; see `keprix-projects/fleetz/` |
| NHS / COMPASS | Clinical safety copilot | Planned Keprix consumer; see `keprix-projects/NHS/` |
| Carina | Commercial platform | Separate commercial workspace and managed product line |
| Aiva | Commercial AI employee | Powered by Carina, never built on Keprix |
| Labyrinth Scout | Governance product | Standalone trust, policy, audit, kill switch, and evidence layer |
| Keprix Hub | Ecosystem layer | Packs, playbooks, adapters, tools, templates, and marketplace |

All vertical products live under `keprix-projects/`. See `keprix-projects/README.md`
for integration pattern and minimum Keprix surface.

Build principle: keep product boundaries clear so Keprix does not become a confusing bundle of every commercial product.

## Prompt Groups By Architecture Layer

| Prompt Range | Category | Architecture Layer |
| --- | --- | --- |
| `00` to `07` | Foundation and kernel | Keprix Core |
| `08` to `14` | Workspace and local services | Distribution and services |
| `15` to `20` | API, SDK, integrations, hardening | Kernel and developer platform |
| `21` to `30` | Security prompts moved to Petraclus | Product boundary |
| `31` to `35` | UI, commands, notifications, localisation | UI surfaces |
| `36` to `40` | Self-building, domain packs, evals, data/ML | Developer platform and services |
| `41` to `44` | Installer, docs, community, marketplace | Distribution and Hub |
| `45` to `46` | Product boundary audit and optional Scout connector | Commercial boundaries |
| `47` to `49` | Removed and archived | Not implemented in Keprix |
| `50` to `51` | Support and productisation | Distribution readiness |
| `52` to `63` | Opportunity Engine | Workspace app built on playbooks |
| `64` to `72` | Reference-agent adoption sprint | Kernel, services, UI, Hub, evals |
| `73` to `74` | Marketing site | Distribution readiness |
| `75` to `85` | Agent personas | Workspace app: specialised agent identities |
| `86` | External human review gateway | Layer 7: governance and trust |
| `87` | PDF and structured document export | Layer 3: workspace documents |
| `88` | GDPR compliance infrastructure | Layer 7: governance and trust |
| `89` | Legal acceptance gate | Layer 7: governance and trust |
| `90` | Scout evidence pack and clinical event taxonomy | Layer 7: governance and trust |
| `91` | Clinical pack gate | Layer 5: Hub (skill pack system) |
| `92` | Outbound notify external | Layer 2: system services (notification) |
| `93` | African language provider adapters (SeamlessM4T, NLLB-200) | Layer 2: system services (localization) |
| `94` | Structured intent extraction engine | Layer 1: kernel (localization) |
| `95` | Voice template system | Layer 2: system services (localization) |
| `96` | Localization data flywheel and correction loop | Layer 7: governance and trust |
| `97` (AbbiS product) | borehole-africa domain pack localization layer | Keprix Hub: domain pack |
| `97` | Agent migration manifest (Hermes, OpenClaw, Markdown adapters) | Layer 2: system services (migration) |
| `98` | Coding posture detection and runtime mode resolution | Layer 1: kernel (agent runtime) |
| `99` | Research task registry with session persistence and SSE stream | Layer 2: system services (research) |
| `100` | Ambient room events in group channels | Layer 2: system services (messaging) |
| `101` | Voice wake words with gateway ownership and node broadcast | Layer 2: system services (voice) |
| `102` | Hot backup and restore with SQLite backup API | Layer 2: system services (ops) |

## Recommended Build Order From Here

Do not build by newest prompt first. Build by dependency:

1. Keprix Core: `00` to `08`.
2. Kernel safety and API: `02`, `05`, `16`, `20`.
3. Durable playbook runtime: `64`.
4. Crews, flows, and multi-agent messaging: `65`, `71`.
5. Workspace basics: `09` to `13`.
6. Tool adapters and integrations: `15`, `69`.
7. Browser, analytics, and coding services: `66`, `67`, `68`.
8. UI surfaces: `31`, `32`, `33`, `62`.
9. Opportunity Engine: `52` to `63`.
10. Evals and observability: `39`, `70`.
11. Installer, docs, community, marketplace: `41` to `44`.
12. Product boundary audit and optional Scout connector: `45`, `46`.
13. Keep removed commercial stubs archived: `47` to `49`.
14. Final support and productisation: `50`, `51`, `72`.
15. Compliance and governance infrastructure (build after `46` and `34`):
    a. GDPR infrastructure: `88` (depends on vault `08` and audit log `02`).
    b. Legal acceptance gate: `89` (depends on `88` for consent ledger integration).
    c. Outbound notify external: `92` (depends on vault `08` and notifications `34`).
    d. External human review gateway: `86` (depends on `92`, `88`, `87`, and playbook runtime `64`).
    e. PDF and structured document export: `87` (depends on workspace documents `09`).
    f. Scout evidence pack and clinical event taxonomy: `90` (depends on `46`, `88`, `89`).
    g. Clinical pack gate: `91` (depends on skill loader `07`, notifications `34`, `92`).
16. Localization (build after `35` and `07`):
    a. African language provider adapters: `93` (depends on vault `08`, config `06`).
    b. Structured intent extraction engine: `94` (depends on domain pack loader `07`, LLM tool dispatch `03`).
    c. Voice template system: `95` (depends on file store `09`, notifications `34`, `93`).
    d. Localization data flywheel: `96` (depends on localization audit from `35`, `93`, `94`).
    e. borehole-africa domain pack localization layer: `97` (AbbiS product; depends on `93`, `94`, `95`, `96`).
17. Reference agent gap fills (build after their direct dependencies are stable):
    a. Agent migration manifest: `97` (depends on memory `06`, skill loader `07`, document store `09`).
    b. Coding posture detection: `98` (depends on agent loop `03`, provider router `04`).
    c. Research task registry: `99` (depends on deep research `12`, document store `09`, SSE from `16`).
    d. Ambient room events: `100` (depends on messaging gateway `11`, tool registry `05`).
    e. Voice wake words: `101` (depends on voice pipeline `35`, node bus from `16`).
    f. Hot backup and restore: `102` (depends on vault `08`, cron `13`).

## What Counts As Fully Built

A prompt is fully built only when:

- Code exists in the correct layer.
- Tests exist for risky or shared behaviour.
- Docs or UI text use the correct product terminology.
- Approval gates are present for risky actions.
- No secrets are hardcoded.
- The feature works from the expected entry point.
- The prompt can be archived into `prompts-archive` under the correct product group.
