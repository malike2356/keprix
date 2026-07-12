"""Generate Keprix self-knowledge documents from live code introspection.

Each document becomes one or more RAG chunks. Ingested with
source_type="keprix_self" so the retriever can filter by it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class KnowledgeDocument:
    source_id: str
    title: str
    content: str
    category: str


def _nav_documents() -> list[KnowledgeDocument]:
    """Generate capability map from the live navigation registry."""
    try:
        from keprix.ui_contract.navigation import NAV_ITEMS, NAV_GROUP_LABELS
    except Exception:
        return []

    by_group: dict[str, list[dict[str, Any]]] = {}
    for item in NAV_ITEMS:
        g = item.get("group", "other")
        by_group.setdefault(g, []).append(item)

    docs = []
    for group, items in by_group.items():
        label = NAV_GROUP_LABELS.get(group, group.title())
        lines = [f"# Keprix {label} Features\n"]
        for item in items:
            lines.append(f"- **{item['label']}** - route: `{item['href']}`")
        docs.append(KnowledgeDocument(
            source_id=f"nav_group_{group}",
            title=f"Keprix {label} Features",
            content="\n".join(lines),
            category="capabilities",
        ))

    # One combined summary doc
    all_lines = ["# Keprix Full Navigation and Route Map\n",
                 "All available pages and features in Keprix:\n"]
    for item in NAV_ITEMS:
        g = item.get("group", "")
        all_lines.append(f"- **{item['label']}** ({g}): `{item['href']}`")
    docs.append(KnowledgeDocument(
        source_id="nav_full_map",
        title="Keprix Full Navigation and Route Map",
        content="\n".join(all_lines),
        category="capabilities",
    ))
    return docs


def _feature_flag_document() -> KnowledgeDocument:
    """Generate feature flag reference from live registry."""
    try:
        from keprix.feature_flags.registry import KNOWN_FLAGS
        from keprix.feature_flags.store import FeatureFlagStore
        overrides = FeatureFlagStore().load_overrides()
    except Exception:
        KNOWN_FLAGS = []  # type: ignore[assignment]
        overrides = {}

    lines = ["# Keprix Feature Flags\n",
             "Feature flags gate progressive user/operator UI surfaces (nav and related pages).",
             "They are not a 1:1 map of every backend package, plugin, or CLI module.",
             "Admins/owners always receive the full navigation contract.",
             "Admins can toggle flags at /admin/feature-flags (grid or list view).",
             "Wider catalog: /settings/modules and /developer/module-inventory.\n"]

    by_cat: dict[str, list] = {}
    for f in KNOWN_FLAGS:
        by_cat.setdefault(f.category, []).append(f)

    for cat, flags in sorted(by_cat.items()):
        lines.append(f"\n## {cat.title()}")
        for f in flags:
            state = "OVERRIDDEN to " + str(overrides[f.id]) if f.id in overrides else f"default={f.default}"
            lines.append(f"- **{f.id}** ({state}): {f.description}")

    return KnowledgeDocument(
        source_id="feature_flags",
        title="Keprix Feature Flags",
        content="\n".join(lines),
        category="configuration",
    )


def _identity_document() -> KnowledgeDocument:
    content = """\
# Keprix Identity and Architecture

Keprix is an open-source AI agent operating system (agent OS) built by VERLOX Ltd.
GitHub: https://github.com/malike2356/keprix
License: MIT
Current version: 0.16.0

## What Keprix Is

Keprix is not a chatbot or assistant framework. It is an agent OS:
- It synthesises new tools on demand and installs them live
- It manages persistent workspaces with memory across sessions
- It runs automations, cron jobs, playbooks, and background tasks
- It integrates with external services through typed connections
- It supports multi-user, multi-workspace deployments

## Architecture

- Backend: FastAPI + Python 3.11, runs at localhost:3333
- Frontend: Next.js 14 + TypeScript + MUI, runs at localhost:3000
- Database: PostgreSQL (sessions, conversations, data)
- Cache: Redis (job queues, session cache)
- Embeddings: EmbeddingService (Gemini primary, OpenAI fallback, deterministic fallback)
- RAG store: SQLite at ~/.keprix/rag_pipeline/chunks.sqlite (default)
- Knowledge graph: Graphiti (in brain/ module)
- Config: ~/.keprix/ (persistent home), /opt/lampp/htdocs/verlox/keprix-data/ (runtime data)

## System Prompt Tiers

The agent system prompt has three tiers (built once per session for cache warming):
1. stable: identity (SOUL.md), tool guidance, skills, env hints
2. context: AGENTS.md / .cursorrules, caller system_message
3. volatile: memory snapshot, USER.md, external memory provider, timestamp

## Default Provider

KEPRIX_DEFAULT_PROVIDER=deepseek (DeepSeek API, sk-* key in .env)

## Key Environment Variables

- KEPRIX_DATA_DIR: /opt/lampp/htdocs/verlox/keprix-data/ (persistent)
- KEPRIX_DATABASE_URL: postgresql+asyncpg://keprix:changeme@localhost:5432/keprix
- KEPRIX_REDIS_URL: redis://localhost:6379/0
- KEPRIX_BILLING_ENABLED: true
- KEPRIX_MULTI_USER: true
- KEPRIX_DEVELOPER_MODE: true
- KEPRIX_EMBEDDING_DETERMINISTIC: falls back to hash-based if no Gemini/OpenAI key
"""
    return KnowledgeDocument(
        source_id="identity_architecture",
        title="Keprix Identity and Architecture",
        content=content,
        category="identity",
    )


def _agent_os_document() -> KnowledgeDocument:
    content = """\
# Keprix Agent OS

The Agent OS is Keprix's core layer for managing AI agents in a workspace.

## Onboarding Checklist (14 steps across 5 levels)

Level 0: Foundation
- l0_onboard: Complete the onboard interview (Day 1) - auto-completes when KEPRIX_SETUP_COMPLETE=true

Level 1: First actions
- l1_audit: Complete a workflow audit (/agent-os/audit)
- l1_first_skill: Approve your first skill proposal (/agent-os/skill-proposals)
- l1_promote: Promote a skill to an automation (/agent-os/promote)
- l1_baseline: Set a loop baseline on an automation (/agent-os/loop-profiles)

Level 2: Workspace setup (Day 2-7)
- l2_workspace: Create a Knowledge Pipeline workspace (/workspace/new)
- l2_vault: Connect your vault folder (/settings/vault)
- l2_connect_one: Wire your first connection (/agent-os/connections)
- l2_four_cs_audit: Run a Four C's maturity audit (/agent-os/maturity)
- l2_wiki: Add your first wiki article (/documents)

Level 3: Power use
- l3_pin: Pin an action on the board (/agent-os)
- l3_headless: Run an action headless (/agent-os)
- l3_schedule: Schedule a recurring action (/agent-os)

Level 4: Team and export
- l4_kit: Export a client kit OR invite a teammate (/settings/agent-os/client-kit)

## Key Agent OS Features

- Workflow Audit: Structured audit of how AI can handle 30% of manual work
- Skill Proposals: AI proposes new skills based on observed patterns
- Skill Review: Review and approve/reject proposed skills
- Automations: Promoted skills that run on a loop with baselines
- Loop Profiles: Baselines for automation quality tracking
- Run Ledger: Log of all headless/background agent runs
- Maturity Audit: Four C's (Capability, Coverage, Confidence, Cost) assessment
- Connections: External domain connections (APIs, platforms, services)
- Action Board: Pinned quick-launch actions
- Client Kit: Exportable kit for sharing agent capabilities with clients

## Onboarding Persistence

Onboarding progress is stored in ~/.keprix/users/<user_id>/agent-os-onboarding.json
Dismiss state persists across reboots because ~/.keprix/ is the persistent home.
"""
    return KnowledgeDocument(
        source_id="agent_os",
        title="Keprix Agent OS",
        content=content,
        category="agent_os",
    )


def _api_routes_document() -> KnowledgeDocument:
    content = """\
# Keprix API Routes Reference

All routes served at http://localhost:3333/api/

## Authentication
- POST /api/auth/login - username/password login, returns bearer token
- POST /api/auth/logout
- GET /api/auth/session
- POST /api/auth/register
- GET /api/auth/sso/callback
- POST /api/auth/totp/verify

## Health and Status
- GET /api/health - system health (version, uptime, scout status)
- GET /api/ui/contract - full UI contract (navigation, feature_flags, installed_apps)
- GET /api/ui/module-inventory - all built modules with GUI status

## Agent OS
- GET /api/agent-os/onboarding - onboarding progress for current user
- POST /api/agent-os/onboarding/step/{step_id} - mark step complete
- POST /api/agent-os/onboarding/dismiss - dismiss banner
- GET /api/agent-os/audit - workflow audits
- POST /api/agent-os/audit - create audit
- GET /api/agent-os/skill-proposals - skill proposals queue
- POST /api/agent-os/skill-proposals/{id}/approve
- POST /api/agent-os/skill-proposals/{id}/reject
- GET /api/agent-os/loop-profiles - automation loop profiles
- GET /api/agent-os/runs - headless run ledger
- GET /api/agent-os/maturity - maturity audits
- GET /api/agent-os/connections - domain connections

## Upgrade System
- GET /api/keprix/upgrade/status - current version (0.16.0), available alerts
- GET /api/keprix/upgrade/wizard?target={version} - wizard steps for target version
- POST /api/keprix/upgrade/dry-run - preflight check (async, non-blocking)
- POST /api/keprix/upgrade/execute - execute upgrade (async, non-blocking)
- POST /api/keprix/upgrade/rollback - rollback last upgrade
- GET /api/keprix/upgrade/alerts - pending upgrade alerts
- GET /api/keprix/upgrade/modules - module catalog with GUI status

## A2A
- GET /api/a2a/status - agent and task counts
- GET /api/a2a/agents - list agent cards
- POST /api/a2a/agents - register agent card
- DELETE /api/a2a/agents/{agent_id} - unregister (not keprix-local)
- GET /api/a2a/tasks - list tasks
- POST /api/a2a/tasks - create task (optional agent_id starts it)
- GET /api/a2a/tasks/{task_id} - task detail and artifacts
- POST /api/a2a/tasks/{task_id}/cancel - cancel pending/running task

## Brain
- GET /api/brain/graph - workspace knowledge graph
- GET /api/brain/graph/node/{kind}/{node_id} - node detail
- GET /api/brain/graph/neighbours/{kind}/{node_id} - neighbourhood
- GET /api/brain/health - health report
- POST /api/brain/health/delete-orphans - delete orphans
- POST /api/brain/health/merge-duplicates - merge duplicates
- POST /api/brain/health/archive-stale - archive stale nodes

## Observability
- GET /api/observability/dashboard - usage and cost summary
- GET /api/observability/traces - list traces
- GET /api/observability/traces/{run_id} - trace detail
- POST /api/observability/traces/{run_id}/export - export trace

## Governance / Scout
- GET /api/governance/status - {enabled, connected, provider_endpoint, policies, kill_state}
- POST /api/governance/connect - connect Scout (api_key, provider_endpoint)
- POST /api/governance/disconnect - disconnect Scout
- GET /api/governance/policies - active policies
- POST /api/governance/kill-relay - receive kill directives from Scout

## Feature Flags (Admin)
- GET /api/admin/feature-flags - list all flags with effective_value, overridden status
- PATCH /api/admin/feature-flags/{flag_id} - set {enabled: bool}
- DELETE /api/admin/feature-flags/{flag_id} - reset to runtime default
- POST /api/admin/feature-flags/reset-all - clear all overrides

## Self-Knowledge / RAG
- GET /api/self-knowledge/status - ingestion status and document count
- POST /api/self-knowledge/ingest - trigger re-ingestion of all self-knowledge
- GET /api/self-knowledge/search?q={query} - search self-knowledge docs

## RAG Pipeline
- GET /api/rag-pipeline/connectors - list available connectors
- GET /api/rag-pipeline/stores - list store kinds (memory/sqlite/postgres/pgvector)
- POST /api/rag-pipeline/ingest - ingest a document
- POST /api/rag-pipeline/query - query the pipeline
- POST /api/rag-pipeline/ingest/notion - ingest from Notion

## Billing
- GET /api/billing/status - subscription and plan status
- GET /api/billing/portal/account|invoices - account and invoices
- POST /api/billing/portal/checkout|trial|cancel|resume|payment-method - portal actions
- GET /api/billing/wallet/status|ledger - managed AI credits (hosted)
- POST /api/billing/wallet/purchase - credit top-up
- GET /api/billing/admin/catalog - Stripe catalog pins (admin/owner)
- GET/PUT /api/billing/admin/pricing - plan price pins into billing.yaml (admin/owner)
- POST /api/billing/webhook - Stripe webhook endpoint

## Admin
- GET /api/admin/users - list users
- POST /api/admin/users - create user
- GET /api/admin/quotas - usage quotas
- GET /api/admin/backup - backup status
- POST /api/admin/backup - trigger backup
- GET /api/admin/mcp - MCP server configurations
- GET /api/admin/tools - registered tools
- GET /api/admin/network-egress - egress rules
- GET /api/admin/cron - scheduled jobs
- POST /api/admin/cron - create cron job

## Conversations and Chat
- GET /api/conversations - list sessions
- POST /api/conversations - create session
- GET /api/conversations/{id} - get session with messages
- DELETE /api/conversations/{id}
- POST /api/chat - chat inference endpoint (streaming)

## Workspace and Documents
- GET /api/workspace - workspaces
- POST /api/workspace - create workspace
- GET /api/documents - list documents
- POST /api/documents - upload document
- GET /api/vault - vault configuration
- POST /api/vault/configure - set vault root path

## Voice
- POST /api/voice/transcribe - STT transcription
- POST /api/voice/synthesise - TTS
- GET /api/voice/templates - voice templates
- GET /api/voice/wake-words - configured wake words

## Usage and Analytics
- GET /api/usage - usage statistics
- GET /api/analytics/dashboard - analytics data

## Public API (v1)
- GET /api/v1/health
- POST /api/v1/chat - public chat endpoint (requires API key)
"""
    return KnowledgeDocument(
        source_id="api_routes",
        title="Keprix API Routes Reference",
        content=content,
        category="api",
    )


def _tools_document() -> KnowledgeDocument:
    """Generate tool list from the tools directory."""
    import os
    from pathlib import Path

    tools_dir = Path(__file__).parent.parent / "tools"
    tool_files = []
    if tools_dir.exists():
        tool_files = [f.stem for f in sorted(tools_dir.glob("*.py"))
                      if not f.stem.startswith("_") and f.stem != "tool"]

    content = """\
# Keprix Agent Tools

Keprix ships with a comprehensive toolset available to the agent.

## Tool Categories

### File and Code Tools
- read_file, write_file, edit_file, list_files - filesystem operations
- execute_code, run_terminal - code execution and shell
- search_code, grep_files - code search

### Web and Research
- web_search (Tavily) - web search with configured TAVILY_API_KEY
- fetch_url - fetch web content
- browser tools - AI-controlled browser

### Memory and RAG
- memory (read/write/search) - persistent memory store
- rag_search - search RAG document store
- session_search - search past conversation transcripts

### Communication
- send_email - email via configured integration
- send_message - messaging (WhatsApp, Slack, Discord)

### Document and Media
- read_pdf, parse_document - document parsing
- vision_analyze - image analysis
- transcribe_audio - STT transcription

### Agent OS
- create_skill, run_skill - skill management
- schedule_job, list_jobs - cron scheduling
- ingest_document - RAG ingestion
- run_playbook - playbook execution

### External Services
- github_tools - GitHub integration
- google_workspace - Google Calendar, Drive, Gmail
- notion_tools - Notion pages and databases

### Development
- run_tests, lint_code - code quality
- generate_docs - documentation generation
"""

    if tool_files:
        content += f"\n## Discovered Tool Modules ({len(tool_files)})\n"
        content += "\n".join(f"- {t}" for t in tool_files)

    return KnowledgeDocument(
        source_id="agent_tools",
        title="Keprix Agent Tools",
        content=content,
        category="tools",
    )


def _settings_document() -> KnowledgeDocument:
    content = """\
# Keprix Settings and Configuration

## Settings Pages (/settings/*)

### Account Settings (/settings/account)
- Profile: display name, avatar, timezone, locale
- Password: change password
- Sessions: view and revoke active sessions
- Two-Factor: TOTP 2FA setup (KEPRIX_REQUIRE_2FA=false by default)
- Connected Accounts: OAuth/SSO linked accounts

### Billing (/settings/billing)
Stripe billing UI. Requires KEPRIX_BILLING_ENABLED=true.
Price IDs come from the Verlox catalog (.stripe-credentials-and-price-id.md); pin in billing.yaml.
Admins/owners can pin catalog prices via the pricing panel (GET/PUT /api/billing/admin/pricing).
Keprix Community Donation: £1 one-off (price_1Tri9T2WMXleLh8eA6gCXHbk); voluntary.
Pro example: £49/mo and £449/yr catalog pins. Monthly/yearly toggle only when interval exists.

### Modules (/settings/modules)
Catalog of packages and surfaces beyond the curated sidebar. Complements Developer → Module inventory.
Statuses: available (dedicated GUI), partial (incomplete UI), cli_api (CLI/API only).
Examples available: SSO (/settings/account/connected-accounts), Notion (/integrations?id=notion),
A2A (/a2a), Observability (/observability). Restart the API after catalog code changes.
Feature flags do not list every module; see progressive disclosure policy.

### Governance (/settings/governance)
Scout governance integration. Controls: kill switches, audit trails, operator policies.
When disabled (enabled=false, connected=false): badge shows "Local" (community edition default).
When pending (enabled=true, connected=false): badge shows "Scout pending".
To connect: POST /api/governance/connect with {api_key, provider_endpoint}.

### Upgrade (/settings/upgrade)
Upgrade wizard UI. Current version: 0.16.0.
Upgrade flow: dry-run (availability check) -> execute (pip install + migration).
Both run inside asyncio.to_thread() to avoid blocking the event loop.

### Vault (/settings/vault)
File vault: a local folder Keprix watches for documents to index.
Set vault root path via POST /api/vault/configure.

### Modules (/settings/modules)
Read-only catalog of installed modules and their GUI status (available/partial/CLI only).
Open A2A and Observability from here when they are marked available.

### Voice (/settings/voice)
- Voice numbers: inbound phone numbers (Twilio integration)
- Receptionist: AI receptionist configuration
- Wake words: custom wake word detection
- Voice templates: saved voice profiles

### Web Search (/settings/web-search)
Configure Tavily API key and search preferences.
Current: TAVILY_API_KEY=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

### Integrations (/settings/integrations)
- Google Workspace: Calendar, Drive, Gmail OAuth

### Localization (/settings/localization)
- Metrics: unit system (metric/imperial)
- Corrections: custom AI output corrections

### Notifications (/settings/notifications)
- In-app notifications
- External: webhook, Slack, Discord, email

### Users (/settings/users)
Multi-user management. KEPRIX_MULTI_USER=true enables this.
Default admin: lordsesame@gmail.com

### Developer (/settings/agent-os/client-kit)
Export client kit: ZIP package of agent capabilities for sharing.

## Key Config Files

- /opt/lampp/htdocs/verlox/keprix/.env - all environment variables
- /opt/lampp/htdocs/verlox/keprix/config/products.yaml - product/extension registry
- /opt/lampp/htdocs/verlox/keprix/config/billing.yaml - billing configuration
- ~/.keprix/SOUL.md - agent identity (overrides DEFAULT_AGENT_IDENTITY)
- ~/.keprix/feature_flags.json - runtime feature flag overrides
- ~/.keprix/rag_pipeline/chunks.sqlite - RAG document store
"""
    return KnowledgeDocument(
        source_id="settings_configuration",
        title="Keprix Settings and Configuration",
        content=content,
        category="configuration",
    )


def _workspace_document() -> KnowledgeDocument:
    content = """\
# Keprix Workspace and Knowledge Features

## Knowledge Pipeline (/rag-pipeline)
Haystack-style RAG pipeline with:
- Converter: parse text, markdown, HTML, email, CSV
- Cleaner: normalise and clean content
- Splitter: chunk with configurable token size (default 512) and overlap (64)
- Embedder: EmbeddingService (Gemini → OpenAI → deterministic hash fallback)
- Retriever: vector + keyword hybrid search
- Ranker: rerank by relevance score
- Generator: LLM answer synthesis

Store backends: memory (default/test), sqlite (~/.keprix/rag_pipeline/chunks.sqlite),
postgres, pgvector, external vector adapter.

## Documents (/documents)
Upload and manage files. Supports PDF, markdown, text, CSV, HTML.
Files in the vault folder are auto-indexed.

## Vault (/vault)
A watched local folder. Any .md file in the vault triggers auto-indexing into wiki.
Configure root path at /settings/vault.

## Brain / Knowledge Graph (/brain)
Shared Graph | List | Health tabs:
- /brain/graph - interactive knowledge graph (layouts, clusters, filters)
- /memory - memory list browser (Brain list tab)
- /brain/health - orphans, duplicates, coverage, archive stale nodes
- /brain/graphiti - Graphiti session replay and ingestion
API: /api/brain/graph, /api/brain/health, /api/brain/graphiti/*
Graphiti bridge at src/keprix/brain/graphiti_bridge.py

## A2A (/a2a)
Agent registry and task board. API under /api/a2a (agents, tasks, status, cancel).
Listed as available in Settings → Modules.

## Observability (/observability)
Dashboard and recent traces via /api/observability/*. Complements /evals.
Listed as available in Settings → Modules.

## Research Projects (/research)
AI-assisted research workspace:
- Create research projects with objectives
- AI performs structured research using web search and documents
- Results saved as project artifacts

## Notes (/notes)
Simple note management with markdown support and AI assistance.

## Memory System (/memory)
Persistent agent memory across sessions. Page title is Brain; Graph | List | Health tabs
link to /brain/graph, /memory, and /brain/health.
Memory providers: built-in (default), Honcho, Hindsight, Mem0 (external plugins).
Memory is injected into the volatile tier of every agent's system prompt.

## Workspace Templates (/workspace/new)
Pre-configured workspace types:
- personal-os: personal productivity setup
- data-pipeline: RAG and ingestion focused
- crm-workspace: contacts and opportunities
"""
    return KnowledgeDocument(
        source_id="workspace_knowledge",
        title="Keprix Workspace and Knowledge Features",
        content=content,
        category="workspace",
    )


def _billing_document() -> KnowledgeDocument:
    content = """\
# Keprix Billing and Stripe Configuration

Keprix uses Stripe for billing. All price IDs and amounts come from the Verlox
catalog file `.stripe-credentials-and-price-id.md` (not committed with secrets).

NEVER create new Stripe prices. Only pin existing price_* IDs into config/billing.yaml
or via the admin pricing GUI on /settings/billing.

## Environment (names only; values live in .env)

- KEPRIX_BILLING_ENABLED / KEPRIX_BILLING_PROVIDER
- KEPRIX_BILLING_CONFIG (default config/billing.yaml)
- STRIPE_SECRET_KEY, STRIPE_PUBLISHABLE_KEY, STRIPE_WEBHOOK_SECRET

## Keprix Community Donation
Open-amount voluntary support (min £1, max £500) via Checkout price_data.
POST /api/billing/donation/checkout { amount_gbp, donation_id? }.
Documentary £1 catalog pin: price_1Tri9T2WMXleLh8eA6gCXHbk (not used for open amounts).
Never gates usage.

## Verlox SaaS plan pins (examples; confirm against catalog)

- Pro: £49/mo (price_1Trhnm2WMXleLh8eevN9oBYd), £449/yr (price_1Trhnl2WMXleLh8e9zAYG7F4)
- Team: £129/mo (price_1Trhnm2WMXleLh8etXFvF1VN) and yearly catalog pin
- SSO / extra seat / top-ups: catalog only

## Admin pricing API

- GET /api/billing/admin/catalog
- GET/PUT /api/billing/admin/pricing (writes billing.yaml; admin/owner only)

## Billing Settings Page (/settings/billing)

Requires billing enabled and (for live checkout) Stripe keys.
Portal checkout, invoices, payment method, managed AI wallet on hosted.
Monthly/yearly toggle only when that interval exists for the plan.
"""
    return KnowledgeDocument(
        source_id="billing_stripe",
        title="Keprix Billing and Stripe Configuration",
        content=content,
        category="billing",
    )


def _voice_document() -> KnowledgeDocument:
    content = """\
# Keprix Voice Features

Voice input is enabled when KEPRIX_EMBEDDING_DETERMINISTIC is not required and
an STT provider is configured. Feature flag: voice_input.

## Voice Settings (/settings/voice)

### Numbers
Inbound phone numbers via Twilio. Calls route to the AI receptionist.

### Receptionist
AI voice receptionist configuration:
- Greeting script
- Call handling rules
- Transfer logic

### Wake Words
Custom wake word detection for hands-free activation.

### Voice Templates (/settings/voice-templates)
Saved voice profiles with:
- TTS voice selection
- Speed and pitch settings
- Custom intro/outro messages

## Voice Interface (/voice)
Live voice conversation interface. Streams audio to STT, sends to agent,
streams TTS response back.

## Voice in Chat (/dev/voice-input)
Voice input widget for the main chat interface. Holds a temporary WAV file
at /tmp/keprix-voice-*.wav during recording.

## Voice Routes (API)
- POST /api/voice/transcribe - STT (Whisper or configured provider)
- POST /api/voice/synthesise - TTS
- GET /api/voice/templates - list saved templates
- POST /api/voice/templates - create template
- GET /api/voice/wake-words - configured wake words
"""
    return KnowledgeDocument(
        source_id="voice_features",
        title="Keprix Voice Features",
        content=content,
        category="features",
    )


def _developer_document() -> KnowledgeDocument:
    content = """\
# Keprix Developer Features

## Developer Console (/developer)
Central developer hub with:
- SDK documentation
- API reference
- Module inventory

## SDK (/developer/sdk)
Keprix agent SDK for building custom integrations.

## Module Inventory (/developer/module-inventory)
Live catalog of all Keprix modules with GUI status.
Sourced from GET /api/ui/module-inventory.

## API Documentation (/api/docs)
Interactive Swagger/OpenAPI docs at /api/docs (FastAPI auto-generated).
Also available at localhost:3333/docs when the backend is running.

## Coding Tools (/coding/ladder)
AI coding assistant with:
- Code generation
- Code review
- Refactoring suggestions
- Ladder mode: step-by-step code building

## Evaluations (/evals)
Agent evaluation framework:
- Define eval suites
- Run agents against test cases
- Score and compare outputs

## Feature Flags Admin (/admin/feature-flags)
Runtime toggle for progressive UI surface flags (not every backend module).
Grid or list layout in the admin UI.
Changes persist to ~/.keprix/feature_flags.json immediately.
UI contract reflects changes on next request (no restart needed).
Admins/owners always see full curated navigation regardless of flags.

## Self-Knowledge RAG (/admin/self-knowledge)
Trigger re-indexing of Keprix self-knowledge documents.
Source type: keprix_self in the SQLite RAG store.

## Playbook Studio (/playbooks/studio)
Visual workflow builder for AI-powered automations.
Build multi-step playbooks with branching logic and tool calls.
"""
    return KnowledgeDocument(
        source_id="developer_features",
        title="Keprix Developer Features",
        content=content,
        category="developer",
    )


def _apps_document() -> KnowledgeDocument:
    content = """\
# Keprix Apps and Automation

## Agent Apps Marketplace (/agent-apps)
Third-party agent applications that extend Keprix.
Install apps from the catalog at /agent-apps/install.
Each app has: agents, tools, evals, and playbooks.

Built-in sample apps:
- daily-standup: Generate daily standup reports
- invoice-review: AI invoice review and flagging
- research-brief: Structured research brief generation
- hello-agent: Sample app template

## Installed Apps (/apps/[slug])
Navigate to /apps/{app-slug} to run an installed app.
Sections within an app at /apps/{app-slug}/{section}.

## Builder (/builder)
Background job builder for long-running tasks.
Jobs run asynchronously and report status.
View job details at /builder/jobs/{id}.

## Skills Hub (/skills)
Skills are reusable AI capabilities attached to agent sessions.
- Browse and install skill packs
- Skills inject into the system prompt stable tier
- Create custom skills via Agent OS > Skill Proposals

## Playbooks (/playbooks)
Automated workflow runner.
- /playbooks - list all playbooks
- /playbooks/{runId} - view a specific run
- /playbooks/studio - visual builder
- /playbooks/studio/{id} - edit a specific playbook

## Control Center (/control-center)
Admin overview of all running agents, jobs, and automations.

## Cron Jobs (/admin/cron)
Scheduled recurring tasks.
Jobs stored in ~/.keprix/cron/jobs.json.
API: GET/POST /api/admin/cron

## Agent Runtime (/agent-runtime)
Live view of running agent sessions with tool calls, memory access, and outputs.

## Agent Studio (/agent-studio)
Visual agent designer for creating custom agent configurations.

## Domain Packs (/domain-packs)
Pre-built knowledge and tool packs for specific domains.
Currently available: borehole drilling (Ghana), example compliance.
Configure in config/products.yaml.
"""
    return KnowledgeDocument(
        source_id="apps_automation",
        title="Keprix Apps and Automation",
        content=content,
        category="apps",
    )


def _security_document() -> KnowledgeDocument:
    content = """\
# Keprix Security Architecture

## Authentication
- JWT-based sessions (KEPRIX_JWT_SECRET in .env)
- Session TTL: 7 days (KEPRIX_SESSION_TTL_DAYS)
- Optional TOTP 2FA (KEPRIX_REQUIRE_2FA=false by default)
- SSO via Google OAuth, GitHub OAuth, generic OIDC
- Sessions stored in /opt/lampp/htdocs/verlox/keprix-data/sessions.json

## Multi-user
KEPRIX_MULTI_USER=true enables multiple user accounts.
Roles: viewer, user, admin, owner.
Admin users can access /admin/* routes and /api/admin/* endpoints.

## Vault Encryption
KEPRIX_VAULT_KEY: AES-256 key for vault file encryption.
Vault files stored under the configured vault root path.

## Audit and Isolation
- /admin/isolation-audit: audit agent isolation boundaries
- Egress controls at /admin/network-egress
- Tool ACL controls (governance_policy_registry.blocked_tools)
- Prompt guard (defense layer active by default)

## Governance / Scout Integration
External governance via Labyrinth Scout.
- Kill switches: stop_agent, lock_workspace, disable_tools
- Tamper-evident audit trails streamed to Scout
- Operator policy enforcement on tools and providers
- Status badge: "Local" (no Scout), "Scout pending" (connecting), "Governed" (connected)

Connect Scout: POST /api/governance/connect
{
  "provider_endpoint": "https://api.labyrinthscout.com",
  "api_key": "<your Scout API key>"
}

## Defense Layers (always active)
- prompt_guard: true
- egress_gate: true
- tool_acl: true
- checkpoint_manager: true
- governance_kill_relay: true
- scout_client: false (until Scout connected)
"""
    return KnowledgeDocument(
        source_id="security_architecture",
        title="Keprix Security Architecture",
        content=content,
        category="security",
    )


def _self_knowledge_document() -> KnowledgeDocument:
    """Document describing the self-knowledge RAG system itself."""
    content = """\
# Keprix Self-Knowledge RAG System

Keprix knows its own codebase through a RAG-based self-knowledge system.

## Architecture

Self-knowledge documents are:
1. Generated by src/keprix/self_knowledge/documents.py via code introspection
2. Ingested into the SQLite RAG store (~/.keprix/rag_pipeline/chunks.sqlite)
3. Retrieved on every agent turn via the KeprixSelfKnowledgeLayer
4. Injected into the volatile tier of the system prompt as relevant context

## Source Types

Documents are ingested with source_type="keprix_self".
Categories: identity, capabilities, api, configuration, agent_os,
workspace, billing, tools, features, developer, apps, security.

## Re-indexing

Trigger re-indexing at any time:
- Admin UI: /admin/self-knowledge
- API: POST /api/self-knowledge/ingest (admin only)
- Script: python scripts/ingest-self-knowledge.py

## Retrieval

The KeprixSelfKnowledgeLayer (src/keprix/self_knowledge/layer.py):
- Runs on every turn before the agent responds
- Searches for documents relevant to the current message
- Injects top-3 results into the volatile system prompt tier
- Only activates if source_type="keprix_self" documents exist in the store

## Document Count

Current self-knowledge corpus covers:
- Identity and architecture
- All navigation routes (100+ pages)
- API routes reference
- Feature flags (16 flags)
- Agent OS (14-step onboarding)
- Tools catalog
- Settings and configuration
- Workspace and knowledge features
- Billing and Stripe
- Voice features
- Developer features
- Apps and automation
- Security architecture
"""
    return KnowledgeDocument(
        source_id="self_knowledge_system",
        title="Keprix Self-Knowledge RAG System",
        content=content,
        category="identity",
    )


def generate_all_documents() -> list[KnowledgeDocument]:
    """Return all self-knowledge documents."""
    docs: list[KnowledgeDocument] = [
        _identity_document(),
        _agent_os_document(),
        _api_routes_document(),
        _feature_flag_document(),
        _tools_document(),
        _settings_document(),
        _workspace_document(),
        _billing_document(),
        _voice_document(),
        _developer_document(),
        _apps_document(),
        _security_document(),
        _self_knowledge_document(),
    ]
    # Add navigation group documents
    docs.extend(_nav_documents())
    return docs
