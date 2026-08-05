# Keprix Full Product Map

This page is the current operator map for Keprix Community Edition. It describes the platform as it exists today across the backend runtime, terminal UI, web workspace, security layer, automation surface, integrations, and operations tooling.

## Platform layers

| Layer | What it does | Main surfaces |
| --- | --- | --- |
| Core runtime | Runs agent turns, model routing, tools, memory, sessions, streaming, approvals, and setup state | Python backend, REST API, CLI, TUI |
| Command Center TUI | Terminal workspace for chat, sessions, runtime events, slash commands, diagnostics, tools, and panels | `keprix tui`, local slash commands, backend fallthrough |
| Web workspace | Browser workspace for daily operator work | Chat, documents, notes, tasks, calendar, email, contacts, gallery, memory, brain graph |
| Agent OS | Automation layer for workflows, run ledgers, action boards, onboarding, client kits, agent apps, and self-improvement | Agent OS pages, playbooks, agent apps, skills, plugins |
| Knowledge layer | Stores, indexes, searches, and retrieves workspace and codebase knowledge | Memory, Brain, RAG pipelines, self-knowledge, vault capture |
| Security layer | Keeps tools, credentials, approvals, and data access bounded | Vault, credential proxy, governance, review gateway, ACLs, audit log |
| Channel Shield | Protects inbound channels before messages reach people or agents | Channel Shield page, email and messaging adapters, quarantine workflow |
| Research and data | Supports research projects, datasets, notebooks, reproducibility, and analytics | Research, notebook bridge, model comparison, analytics workspace |
| Integrations | Connects external tools and runtimes without hard-coding product logic into core | MCP, A2A, Google Workspace, Notion, Trello, n8n, Scout, SDK, mobile |
| Operations | Makes the instance observable and maintainable | Admin dashboard, readiness, backups, changelog automation, usage, billing |

## Runtime and interfaces

Keprix has one backend runtime and several operator interfaces:

- `keprix start` runs the FastAPI backend on port `3333`.
- `keprix tui` opens the Textual Command Center.
- The web workspace runs on port `3000` in development.
- The REST API exposes health, chat, memory, tools, setup, usage, billing, governance, and workspace routes.
- Docker Compose runs the standard local stack with Postgres, Redis, ChromaDB, backend, and frontend.

The TUI and web workspace both talk to the same runtime. The TUI is designed for keyboard-first operators; the web workspace is designed for browser workflows, admin pages, and visual review.

## Command Center TUI

The TUI is no longer a small chat wrapper. It is a full terminal Command Center with:

- Streaming chat and session switching.
- Local slash command registry with descriptions, aliases, argument metadata, and examples.
- Backend command fallthrough for runtime commands and skill commands.
- Command palette and keyboard model.
- Workspace cockpit, status bar, runtime timeline, tool cards, debug overlay, and session map.
- Details panel controls for thinking, tools, subagents, and activity.
- Virtual transcript rendering, selection, copy, review mode, search, and transcript export/import hooks.
- External editor compose, external link opening, mouse mode, voice push-to-talk, large paste collapse, and setup handoff.
- HTTP, WebSocket, and in-process runtime transport contracts.
- Error boundaries, loading states, offline states, fault injection tests, terminal resize handling, and performance budgets.

See [Terminal UI](tui.md), [TUI slash commands](../reference/tui-slash.md), [TUI Hermes behavior parity contract](../architecture/tui-hermes-behavior-parity-contract.md), and [TUI surpass Hermes contract](../architecture/tui-surpass-hermes-contract.md).

## Web workspace

The web workspace is the daily browser shell:

- Home and launcher surfaces for discovery.
- Chat with agent streaming, model state, sessions, and voice input.
- Documents, notes, tasks, calendar, email, contacts, and gallery.
- Memory list, Brain graph, RAG pipelines, and codebase self-knowledge.
- Playbooks, Agent Studio, Agent Apps, skills, plugins, MCP, and trigger builder.
- Settings for providers, billing, governance, feature flags, and workspace configuration.
- Admin and operations pages for readiness, users, tools, cron, usage, and observability.

The web workspace should use the shared UI contract and route catalog so navigation, roles, empty states, and loading states remain consistent.

## Agent OS

Agent OS is the product layer that turns the runtime into an operator workflow system:

- Action Board for active work.
- Run Ledger for traceable runs.
- Client kit and promote flows for packaged workflows.
- Agent Studio and Agent Apps for reusable agent experiences.
- Skill-first execution and hub packs for domain capabilities.
- Self-improvement loops that propose skills, tools, and workflow upgrades through review.

Agent OS must extend core through registries, adapters, config, feature flags, and hooks. It must not make generic core modules depend on product-only pages or policies.

## Channel Shield

Channel Shield is the inbound protection layer for email and messaging:

- Route inbound messages through a scanning layer before they reach the final recipient or agent.
- Inspect content, attachments, links, and hidden payloads.
- Use sandboxing, malware analysis, and policy checks where configured.
- Quarantine suspicious messages and emit a safe summary plus evidence.
- Keep scanning idle when `enabled: false`; configuration controls enforcement.

Use Channel Shield for preventative protection. Use incident and forensics tooling when damage control is already underway.

## Security, governance, and credentials

Keprix separates normal operator work from high-risk actions:

- Vault and credential proxy keep secrets out of tools and prompts.
- Credential rotation, vault migration, and purge flows support maintenance.
- Review gateway requires approval for sensitive actions.
- Tool ACLs and resource ACLs gate tool access by scope.
- Egress, network, file, prompt, and output guards constrain agent behavior.
- Scout integration can receive sanitized governance signals and control actions.
- Audit logs, readiness checks, and hardening docs support production review.

## Knowledge and memory

The knowledge layer includes:

- Structured workspace memory.
- Brain graph views.
- RAG pipelines for documents, workspace data, and codebase self-knowledge.
- Hot cache and vault auto-capture layers.
- Research notebooks, datasets, citation bridges, and reproducibility workflows.

Memory is workspace scoped. Retrieval should respect tenant, product, and role boundaries.

## Automation and integrations

Keprix automation spans:

- YAML and visual playbooks.
- Cron jobs, webhooks, triggers, and scheduled runs.
- MCP connectors and optional MCP sidecars.
- A2A providers and agent teams.
- Google Workspace, Notion, Trello, n8n, Scout, SDK, mobile, and OpenAI-compatible API routes.
- Local models through Ollama and OpenAI-compatible endpoints.

Integrations should be connector-first where possible, with credentials flowing through the credential proxy or vault.

## Operations and validation

Use these checks after product or docs changes:

```bash
python -m pytest tests/tui -q
bash scripts/check-tui-surpass-hermes.sh
bash scripts/build-docs.sh
cd frontend && pnpm type-check
```

For full product work, add focused tests for the touched area: billing, auth, Channel Shield, Agent OS, tools, memory, playbooks, security, or frontend UI contracts.
