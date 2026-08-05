# Keprix Build Prompts

This folder contains the ordered build prompts for Keprix.

**Start here:** `00a-product-vision-and-agent-consolidation-map.md`, then `00b-full-build-scope-and-build-order.md`, then `00-project-setup-architecture-and-developer-access.md`.

Before executing any prompt, read `../../docs/ENGINEERING-PILLARS.md` and `PROMPT-CROSSREF-GUIDE.md`.

## Execution Rule

Build in numeric order unless a prompt is already fully implemented and verified. Do not skip a capability because it is "later". This order exists so dependencies land before the features that depend on them.

Cybersecurity, forensics, offensive tooling, SIEM, threat intelligence, and target authorization do not belong in active Keprix core prompts. Those prompts live under Petraclus. The old Keprix-side placeholders were preserved in `prompts-archive/moved-to-petraclus/`.

## Phase 0: Orientation and Foundation (00-07)

| File | What It Builds |
| --- | --- |
| `00a-product-vision-and-agent-consolidation-map.md` | Product vision, expanded reference-agent model, boundaries, and build principles. Reference first. |
| `00b-full-build-scope-and-build-order.md` | Full build scope and build-order decision document. Keep aligned with this README. |
| `00-project-setup-architecture-and-developer-access.md` | Repo structure, Docker Compose, env file, developer access flag, naming constants. |
| `06-memory-and-rag.md` | pgvector RAG, episodic memory, knowledge base ingestion, and hybrid search. |

**Completed (implemented):** prompts 01, 02, 14, and 51 moved to ``.
See that folder's README for what landed in `src/keprix/`.

**Archived (Hermes clone, commit `10c60d0`):** prompts 03, 04, 05, 07 moved to
``. The agent spine, providers, tools,
skills, gateway, cron, MCP/ACP, and coding posture code already live under `src/keprix/`.

## Phase 1: Secure Workspace (08-16)

| File | What It Builds |
| --- | --- |
| `08-vault-credentials-and-secrets.md` | AES-256 credential vault, redaction, env injection, secret access audit. |
| `09-agent-managed-credential-setup.md` | Agent-guided credential setup through chat, UI, and CLI. |
| `10-workspace-documents-notes-calendar.md` | Document store, rich notes, calendar sync, task manager, workspace search. |
| `11-email-integration.md` | IMAP/SMTP connector, triage agent, draft composer, inbox rules, thread summarizer. |
| `12-contact-manager-and-sync.md` | Contact store, Google/Outlook/CardDAV/vCard/CSV sync, fuzzy name lookup, confirmation flow, call initiation. |
| `14-deep-research-and-playbook.md` | Web research, source ranking, claim verification, playbook runner, report generator. | Completed: `` |
| `16-self-configuration.md` | Auto-repair, env discovery, dependency health check, optimizer, self-update coordinator. |

**Archived (Hermes clone):** prompt 13 (messaging gateway) and prompt 15 (cron) moved to
``. Gateway and cron code already live under
`src/keprix/gateway/` and `src/keprix/cron/`.

## Phase 2: API, SDK, Product Shell, and Hardening (17-27)

| File | What It Builds |
| --- | --- |
| `18-api-surface-and-observability.md` | REST and WebSocket API, OpenAPI, metrics, tracing, structured logging, health endpoints. |
| `19-openai-compatible-public-api-and-developer-platform.md` | OpenAI-compatible API and developer platform surface. |
| `20-app-foundation-sdk.md` | Python SDK and TypeScript SDK for building apps on Keprix. |
| `21-frontend-ui-and-launchers.md` | Next.js app shell, route layout, launcher, theme system, feature status UI. |
| `22-unified-ui-ux-design-system-and-app-shell.md` | Component library, design tokens, responsive grid, connector configuration patterns. |
| `23-slash-commands.md` | Slash command parser, registry, autocomplete, built-in command set. |
| `24-notifications-inbox-alert-routing-and-escalations.md` | Notification system, alert routing, escalations, delivery channels. |
| `25-mobile-native-apps.md` | iOS and Android apps, push notifications, offline queue, biometric auth. |
| `26-keprix-agent-hardening.md` | Jailbreak prevention, output sanitization, prompt-injection guards, safe tool envelope. |
| `27-localization-language-voice.md` | Base i18n, language detection, translation, voice input/output, language-aware replies. |

**Archived (Hermes clone):** prompt 17 (MCP/ACP) moved to
``.

## Phase 3: Self-Building, Distribution, Boundaries, and Operations (28-46)

| File | What It Builds |
| --- | --- |
| `28-keprix-self-coding-agent.md` | Tool synthesis, sandboxing, tests, approval, live install. |
| `29-project-builder-and-monorepo.md` | AI-assisted scaffolding, monorepo management, dependency graph tooling. |
| `30-domain-knowledge-pack-factory.md` | Domain pack builder for legal, medical, finance, borehole, and other verticals. |
| `31-benchmarks-evals-and-quality-regression-harness.md` | Eval harness, benchmark suite, regression tests, CI integration. |
| `32-combined-data-ml-research-workspace-architecture.md` | Data, ML, analytics, and research workspace architecture. |
| `33-installer-and-zero-to-running.md` | One-command install, Docker path, bare-metal path, setup wizard, updates, rollback. |
| `34-documentation-site-and-landing-page.md` | Docs site, landing page, quickstart, feature comparison. |
| `35-community-infrastructure-and-contribution-guide.md` | Issue templates, PR templates, CONTRIBUTING, SECURITY, release checklist, community onboarding. |
| `36-hub-marketplace-packs-and-template-distribution.md` | Pack registry, submission pipeline, install-from-URL, ratings, pack discovery. |
| `37-aiva-to-keprix-feature-extraction-and-boundary-map.md` | Boundary audit: learn from commercial stack without copying secrets or commercial-only coupling. |
| `38-scout-governance-bridge.md` | Optional paid Scout connector. |
| `39-support-incident-communications-and-customer-success.md` | Support chat, incident log, feedback, diagnostic export. |
| `40-rebranding-and-productization.md` | Brand sweep, copy review, product checklist, release notes, launch checklist. |
| `41-hot-backup-and-restore.md` | Live-safe backups, verification, restore, retention. |
| `42-agent-migration-manifest.md` | Import memory, skills, preferences, and archive documents from other agents. |
| `44-research-task-registry.md` | Persistent research job registry, progress events, cancellation, retention. |
| `45-ambient-room-events.md` | Group-channel ambient context processing without noisy auto-replies. |
| `46-voice-wake-words.md` | Gateway-owned wake word registry and node synchronization. |

## Phase 4: African Language Localization (47-50)

| File | What It Builds |
| --- | --- |
| `47-african-language-provider-adapters.md` | SeamlessM4T, NLLB, language-code mapping, term protection, provider router. |
| `48-structured-intent-extraction-engine.md` | Intent schemas, domain-pack registration, JSON extraction, validators, follow-up generation. |
| `49-voice-template-system.md` | Native speaker template library, fallback matching, hybrid voice assembly, approval workflow. |
| `50-localization-data-flywheel-and-correction-loop.md` | Correction queue, operator review, glossary updates, translation cache, fine-tuning exports, metrics. |

AbbiS product-specific localization lives in `keprix-projects/abbis/prompts/`.

## Phase 5: Core Reference-Agent Adoption (51-59)

| File | What It Builds |
| --- | --- |
| `51-langgraph-style-durable-playbook-runtime.md` | Durable, resumable playbook runtime. | Completed: `` |
| `52-crewai-style-crews-flows-agent-teams.md` | Crews, flows, and agent teams. |
| `53-lavague-style-browser-action-engine.md` | Browser action engine. |
| `54-taskweaver-style-data-analytics-code-workspace.md` | Data analytics and code workspace. |
| `55-swe-agent-style-self-coding-and-patch-trajectories.md` | Patch trajectories for governed self-coding. |
| `56-crewai-tool-library-adapter-pack.md` | Tool library adapter pack. |
| `57-agent-evals-benchmarks-and-trace-observability.md` | Evals, benchmarks, trace observability. |
| `58-autogen-style-multi-agent-messaging-and-studio.md` | Multi-agent messaging and Agent Studio. |
| `59-reference-agent-adoption-release-map.md` | Unified release map for prompts 51-58. |

## Phase 6: Expanded Reference-Agent DNA (60-73)

| File | What It Builds |
| --- | --- |
| `60-reference-agent-gap-audit-and-adoption-matrix.md` | Gap audit, deduplication matrix, licence boundary, build order. |
| `61-openhands-style-agent-control-center.md` | Agent control center, agent servers, automation triggers, run queue. |
| `62-aider-style-git-native-coding-ux.md` | Repo map, git workflow, lint/test loop, watch mode, voice-to-code, context loader. |
| `63-browser-use-style-browser-harness.md` | Browser harness, profiles, browser skills, task benchmarks. |
| `64-smolagents-style-code-agent-and-hub-tools.md` | Code-agent mode, sandbox providers, tool collections, modality inputs, hub packages. |
| `65-openai-agents-style-handoffs-guardrails-tracing-realtime.md` | Handoffs, guardrails, trace viewer, sandbox agents, realtime voice agents. |
| `66-pydantic-ai-style-typed-agents-dependency-injection.md` | Typed agents, dependency injection, schema validation, repair retries, approvals. |
| `67-google-adk-style-agent-lifecycle-and-workflow-app.md` | Agent app manifests, lifecycle hooks, local and web runners, deployment bundles. |
| `68-semantic-kernel-style-plugin-memory-planner-interoperability.md` | Plugin contracts, memory providers, planners, MCP and A2A interoperability. |
| `69-llamaindex-style-document-agents-indexing-and-rag-pipelines.md` | Document parsing, structured extraction, index management, document agents. |
| `70-mastra-style-typescript-agents-workflows-memory-evals.md` | TypeScript SDK agents, workflows, memory, RAG, evals, developer UX. |
| `71-agno-style-agent-platform-interfaces-and-auto-improvement.md` | Interfaces, A2A and AG-UI adapters, monitoring, auto-improvement loops. |
| `72-haystack-style-production-rag-pipelines-and-routing.md` | Production RAG pipelines, routers, document stores, evaluators. |
| `73-expanded-reference-agent-adoption-release-map.md` | Unified release map, smoke test, boundary checks, final integration docs. |

## Phase 7: Research Workspace and Statistical Tools (74-83)

| File | What It Builds |
| --- | --- |
| `74-research-workspace-architecture-and-boundary.md` | Research Workspace architecture, product boundary, data model, UI shell. |
| `75-obsidian-vault-adapter-and-linked-notes.md` | Obsidian vault adapter, Markdown/frontmatter parsing, backlinks, safe note writing. |
| `76-zotero-citations-and-better-bibtex-adapter.md` | Zotero API, local Zotero, Better BibTeX, citation keys, literature notes, bibliography. |
| `77-dataset-codebook-and-survey-manager.md` | Dataset import, codebooks, labels, missing values, lineage, exports. |
| `78-pspp-cli-runner-and-spss-syntax-generator.md` | PSPP syntax generation, CLI runner, output capture, stats artifacts. |
| `79-jamovi-export-bridge-and-r-syntax-workflow.md` | jamovi-ready exports, analysis plans, R syntax capture, module-aware guidance. |
| `80-r-python-jupyter-notebook-runner.md` | R, Python, Jupyter-compatible execution, sandboxing, notebook artifacts. |
| `81-report-generator-pandoc-quarto-and-evidence-bundles.md` | Cited report generator, Pandoc and Quarto adapters, evidence bundles. |
| `82-research-playbooks-ui-and-agent-workflows.md` | Literature review, survey analysis, Obsidian map, PSPP, jamovi, AbbiS research playbooks. |
| `83-research-evals-reproducibility-and-release-map.md` | Research evals, reproducibility checks, smoke test, release map. |

## Phase 8: Opportunity Engine (84-95)

| File | What It Builds |
| --- | --- |
| `84-opportunity-engine-architecture.md` | Opportunity Engine architecture and data model. |
| `85-market-demand-discovery-playbook.md` | Market demand discovery. |
| `86-pain-mining-playbook.md` | Pain mining. |
| `87-offer-and-icp-builder-playbooks.md` | Offer and ICP builder playbooks. |
| `88-competitor-intelligence-playbook.md` | Competitor intelligence. |
| `89-validation-score-playbook.md` | Validation scoring. |
| `90-offer-doc-and-agent-memory-playbook.md` | Offer docs and agent memory. |
| `91-asset-factory-playbook.md` | Asset factory. |
| `92-launch-orchestrator-playbook.md` | Launch orchestration. |
| `93-growth-loop-playbook.md` | Growth loop. |
| `94-opportunity-ui-cli-and-slash-command.md` | Opportunity UI, CLI, slash command. |
| `95-opportunity-engine-tests-docs-and-release.md` | Tests, docs, release readiness. |

## Phase 9: Agent Personas (96-106)

| File | What It Builds |
| --- | --- |
| `96-agent-persona-nexus-orchestrator.md` | NEXUS orchestrator and project control. |
| `97-agent-persona-forge-cto-tech-lead.md` | FORGE CTO and tech lead. |
| `98-agent-persona-warden-ciso-security-lead.md` | WARDEN security lead. |
| `99-agent-persona-sage-research-intelligence.md` | SAGE research intelligence. |
| `100-agent-persona-beacon-marketing-client-delivery.md` | BEACON marketing and client delivery. |
| `101-agent-persona-prism-seo-organic-growth.md` | PRISM SEO and organic growth. |
| `102-agent-persona-compass-strategy-decisions.md` | COMPASS strategy and decisions. |
| `103-agent-persona-ember-wellbeing-coach.md` | EMBER wellbeing coach. |
| `104-agent-persona-echo-voice-receptionist.md` | ECHO voice receptionist. |
| `105-agent-persona-codex-legal-assistant.md` | CODEX legal assistant. |
| `106-agent-persona-scout-governance-kill-switch.md` | SCOUT governance and kill switch persona. |

## Phase 10: Safety, Regulated Workflows, and External Output (107-113)

| File | What It Builds |
| --- | --- |
| `107-external-human-review-gateway.md` | External human review gateway. |
| `108-pdf-and-structured-document-export.md` | PDF and structured document export. |
| `109-gdpr-compliance-infrastructure.md` | GDPR controls, retention, exports, deletion, privacy workflows. |
| `110-legal-acceptance-gate.md` | Legal disclaimer, acceptance, and jurisdiction gating. |
| `111-scout-evidence-pack-and-clinical-event-taxonomy.md` | Evidence pack structure and clinical event taxonomy. |
| `112-clinical-pack-gate.md` | Clinical pack gating, safety controls, release readiness. |
| `113-outbound-notify-external.md` | External notification delivery for approved outbound messages. |

## Phase 11: Public Launch Surface (114-115)

| File | What It Builds |
| --- | --- |
| `114-keprix-marketing-site-brand-and-content.md` | Standalone Keprix marketing site brand, copy, SEO, boundaries. |
| `115-keprix-marketing-site-build-deploy-and-analytics.md` | Static site implementation, deploy script, analytics, sitemap, robots. |

## UI Layer: Frontend Build (116-118, 136-137)

Reference templates (both MIT licensed, cloned to `planning/ui-references/`):
- `saasable-ui/` - SaasAble Free (phoenixcoded): Next.js 16 + React 19 + MUI. AI landing variant + admin shell.
- `flexy-admin/` - Flexy Admin Next.js Free (wrappixel): Next.js 15 + React 19 + MUI + TypeScript. Richer sidebar, data tables, chart widgets.

Port and adapt; do not ship template demo content or branding.

| File | What It Builds |
| --- | --- |
| `116-ui-foundation-theme-and-setup.md` | Next.js scaffold, Keprix MUI dark theme (violet + cyan, slate-900 bg), shared card/scrollbar/logo primitives ported from both templates. |
| `117-marketing-landing-page.md` | Landing page using SaasAble AI variant: terminal hero animation, features grid, how-it-works, integrations strip, OSS band, FAQ, CTA. All copy is Keprix-specific. |
| `118-admin-dashboard-with-flexy.md` | Admin shell: Flexy sidebar + header merged with SaasAble analytics layout. ApexCharts overview dashboard, stat cards, mutation table, auth pages, 4-step first-run setup wizard. |
| `136-agent-conversation-workspace.md` | Agent chat workspace (built from scratch): streaming message feed, ToolCallBlock, CodeBlock, MutationCard with approve/reject, file-attach input bar. |
| `137-admin-workspace-pages.md` | All seven remaining admin pages: Tool Library, Mutation Queue, Memory Store, Channels, API Keys, Users, Settings. Plus global command palette. |

## Product Boundary Notes

- Keprix core is general-purpose AI agent infrastructure.
- Petraclus owns cybersecurity, offensive tooling, case authorization, forensics, SIEM, and threat intelligence.
- AbbiS owns borehole business workflows and product-specific Ghana localization.
- Scout remains a separate paid governance connector.
- Commercial Carina, Aiva, and Scout code should only be used as boundary reference material.

## Implementation Rules

- Never copy secrets, private production config, or private customer data from commercial products.
- Prefer Python/FastAPI for the backend. Frontend is Next.js 14.
- Use "playbook" for model recommendations. Never use "recipe" or "model-recipe".
- Add tests for each prompt before marking it done.
- Keprix has no remote licence tiers. Developer identity is local only.
- Downstream products live in `keprix-projects/` and consume Keprix via SDK or bundled image.
- Follow all seven engineering pillars from `../../docs/ENGINEERING-PILLARS.md`.
- Reference clones for gap analysis live in `../../agents-to-adopt/` (repo path: `planning/agents-to-adopt/`).

