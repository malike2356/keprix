/**
 * Marketing catalog of Keprix capabilities.
 * Landing page shows a short highlight grid; /features lists the full set.
 */

export type MarketingFeature = {
  id: string;
  name: string;
  description: string;
  usedFor: string;
  docsPath?: string;
};

export type MarketingFeatureCategory = {
  id: string;
  title: string;
  summary: string;
  features: MarketingFeature[];
};

export const MARKETING_FEATURE_CATEGORIES: MarketingFeatureCategory[] = [
  {
    id: "runtime",
    title: "Runtime and interfaces",
    summary: "One agent runtime with web, TUI, CLI, and API surfaces.",
    features: [
      {
        id: "agent-runtime",
        name: "Agent runtime",
        description:
          "FastAPI core that runs agent turns, model routing, tools, streaming, sessions, and approvals.",
        usedFor: "The shared brain behind every Keprix interface.",
        docsPath: "features/agent-runtime",
      },
      {
        id: "command-center-tui",
        name: "Command Center TUI",
        description:
          "Keyboard-first Textual terminal with live sessions, slash commands, tool cards, review mode, and diagnostics.",
        usedFor: "Operators who want full control without leaving the terminal.",
        docsPath: "features/tui",
      },
      {
        id: "web-workspace",
        name: "Web workspace",
        description:
          "Browser shell for chat, documents, CRM, automations, settings, and admin pages.",
        usedFor: "Day-to-day operator work in a shared UI contract.",
        docsPath: "features/workspace",
      },
      {
        id: "cli",
        name: "CLI",
        description: "keprix CLI for start, setup, memory, security audit, and operator tasks.",
        usedFor: "Scripted ops, install, and headless administration.",
        docsPath: "reference/cli",
      },
      {
        id: "openai-api",
        name: "OpenAI-compatible API",
        description: "REST and OpenAI-style chat completions against your self-hosted runtime.",
        usedFor: "Connecting external clients and apps to Keprix.",
        docsPath: "integrations/openai-api",
      },
    ],
  },
  {
    id: "workspace",
    title: "Workspace productivity",
    summary: "Daily tools for chat, files, schedule, and people.",
    features: [
      {
        id: "chat",
        name: "Chat",
        description: "Streaming agent sessions with models, tools, slash commands, and voice input.",
        usedFor: "Primary conversational work with the agent.",
        docsPath: "features/chat",
      },
      {
        id: "documents",
        name: "Documents",
        description: "Upload, index, share, and export workspace files.",
        usedFor: "Keeping source material next to the agent.",
        docsPath: "features/documents",
      },
      {
        id: "notes",
        name: "Notes",
        description: "Linked notes and references inside the workspace.",
        usedFor: "Capturing decisions and working context.",
        docsPath: "features/notes",
      },
      {
        id: "tasks",
        name: "Tasks",
        description: "To-do, in progress, and done tracking for operator work.",
        usedFor: "Turning agent outputs into tracked follow-ups.",
        docsPath: "features/tasks",
      },
      {
        id: "calendar",
        name: "Calendar",
        description: "Month, week, and day views with schedule-aware agent context.",
        usedFor: "Planning work and booking-related flows.",
        docsPath: "features/calendar",
      },
      {
        id: "email",
        name: "Email",
        description: "IMAP inbox, AI triage, and send APIs behind Channel Shield where enabled.",
        usedFor: "Reading and acting on mail safely.",
        docsPath: "features/email",
      },
      {
        id: "contacts",
        name: "Contacts",
        description: "People records, sync, and communication preferences.",
        usedFor: "CRM and outreach contact identity.",
        docsPath: "features/contacts",
      },
      {
        id: "gallery",
        name: "Gallery",
        description: "Generated and uploaded images in one browser.",
        usedFor: "Reviewing media produced by agents and tools.",
        docsPath: "features/gallery",
      },
      {
        id: "vical",
        name: "Vical booking",
        description: "Booking pages, reschedule/cancel flows, and Soft Wall enroll hooks.",
        usedFor: "Public scheduling tied to CRM and outreach.",
        docsPath: "features/vical",
      },
      {
        id: "notifications",
        name: "Notifications",
        description: "In-app inbox, digests, and optional external SMTP alerts.",
        usedFor: "Keeping operators aware of approvals and system events.",
        docsPath: "features/notifications",
      },
    ],
  },
  {
    id: "agent-os",
    title: "Agent OS and automation",
    summary: "Workflows, apps, skills, and reviewable self-improvement.",
    features: [
      {
        id: "agent-os",
        name: "Agent OS",
        description:
          "Action boards, run ledgers, client kits, promote flows, and self-improvement loops.",
        usedFor: "Operating agents as a managed workflow system.",
        docsPath: "features/agent-os-overview",
      },
      {
        id: "mutation-engine",
        name: "Mutation engine",
        description:
          "Proposes new tools or code, sandboxes and tests them, then waits for human approval.",
        usedFor: "Closing capability gaps without silent live installs.",
        docsPath: "features/agent",
      },
      {
        id: "self-coding",
        name: "Self-coding agent",
        description: "Long-horizon coding sessions with diffs, tests, and risk review.",
        usedFor: "Repo changes that stay reviewable.",
        docsPath: "features/self-coding-agent",
      },
      {
        id: "playbooks",
        name: "Playbooks",
        description: "Visual and YAML workflows with runs, approvals, schedules, and triggers.",
        usedFor: "Repeatable automations with human checkpoints.",
        docsPath: "features/playbooks",
      },
      {
        id: "cron",
        name: "Cron jobs",
        description: "Scheduled agent tasks with run history.",
        usedFor: "Recurring maintenance and outbound jobs.",
        docsPath: "features/cron-jobs",
      },
      {
        id: "agent-studio",
        name: "Agent Studio",
        description: "Build and publish manifest-driven agent experiences.",
        usedFor: "Packaging reusable agent apps.",
        docsPath: "features/agent-studio",
      },
      {
        id: "agent-apps",
        name: "Agent Apps",
        description: "Install, run, and schedule packaged agent apps.",
        usedFor: "Productized agent workflows for a workspace.",
        docsPath: "features/agent-apps",
      },
      {
        id: "skills",
        name: "Skills and plugins",
        description: "Skills Hub, skill-first execution, and extension plugins.",
        usedFor: "Adding domain behavior without forking core.",
        docsPath: "features/skills",
      },
      {
        id: "improvement-loop",
        name: "Improvement loop",
        description: "Proposes skill, tool, and workflow upgrades through review.",
        usedFor: "Continuous self-improvement under Soft Wall / approvals.",
        docsPath: "features/improvement-loop",
      },
      {
        id: "agent-teams",
        name: "Agent teams",
        description: "Multi-agent collaboration patterns on one runtime.",
        usedFor: "Delegating work across specialized agents.",
        docsPath: "features/agent-teams",
      },
      {
        id: "control-center",
        name: "Control Center",
        description: "Operator cockpit for runtime status and guided actions.",
        usedFor: "Seeing what the fleet of agents is doing.",
        docsPath: "features/control-center",
      },
    ],
  },
  {
    id: "knowledge",
    title: "Knowledge and memory",
    summary: "Recall, graphs, RAG, and self-knowledge about Keprix itself.",
    features: [
      {
        id: "memory",
        name: "Long-term memory",
        description: "Structured, workspace-scoped memory with semantic search.",
        usedFor: "Agents that remember facts across sessions.",
        docsPath: "features/memory",
      },
      {
        id: "brain",
        name: "Brain graph",
        description: "Graph views of entities, memories, and relationships.",
        usedFor: "Exploring how knowledge connects.",
        docsPath: "features/brain",
      },
      {
        id: "rag",
        name: "RAG pipelines",
        description: "Index and retrieve documents, workspace data, and codebase self-knowledge.",
        usedFor: "Grounded answers from your corpus.",
        docsPath: "features/rag-pipelines",
      },
      {
        id: "self-knowledge",
        name: "Self-knowledge",
        description: "Indexed product docs so Keprix can answer what it can do.",
        usedFor: "Operator and agent questions about the platform.",
        docsPath: "features/rag-admin",
      },
      {
        id: "graphiti",
        name: "Graphiti bridge",
        description: "Optional knowledge-graph bridge for richer entity memory.",
        usedFor: "Advanced memory topologies when enabled.",
        docsPath: "features/graphiti-bridge",
      },
    ],
  },
  {
    id: "crm",
    title: "Agentic CRM and outreach",
    summary: "Pipeline, discovery, enrichment, messaging, and Soft Wall safety.",
    features: [
      {
        id: "agentic-crm",
        name: "Agentic CRM",
        description:
          "Leads, contacts, accounts, deals, lists, ICP, SLA, inbox, workflows, analytics, and settings in one CRM surface.",
        usedFor: "Running go-to-market work with agent assistance.",
        docsPath: "features/agentic-crm",
      },
      {
        id: "crm-discovery",
        name: "Discovery and enrich",
        description: "Find and enrich prospects from directories, sheets, and licensed sources.",
        usedFor: "Building qualified pipelines without leaving Keprix.",
        docsPath: "features/discovery-web-directory",
      },
      {
        id: "companies-house",
        name: "Companies House",
        description: "UK company lookup and enrichment against the official API.",
        usedFor: "B2B research and compliance-aware prospecting.",
        docsPath: "features/companies-house",
      },
      {
        id: "outreach",
        name: "Outreach",
        description: "Campaigns, sequences, outbox, replies, suppressions, and deliverability.",
        usedFor: "Controlled multi-channel outbound.",
        docsPath: "features/crm-whatsapp-sms",
      },
      {
        id: "soft-wall",
        name: "Soft Wall",
        description:
          "Approve-then-retry gate for sensitive CRM and mutation actions before they execute.",
        usedFor: "Keeping high-risk writes human-reviewed.",
        docsPath: "features/soft-wall-safety",
      },
      {
        id: "crm-compliance",
        name: "CRM compliance",
        description: "Contactability, suppressions, merges, tracking privacy, and data quality tools.",
        usedFor: "Safer outreach and cleaner CRM data.",
        docsPath: "features/crm-compliance",
      },
      {
        id: "health-social-pack",
        name: "Health and social care pack",
        description: "Domain pack patterns for regulated health/social outreach contexts.",
        usedFor: "Sector-specific CRM and messaging constraints.",
        docsPath: "features/health-social-care-pack",
      },
    ],
  },
  {
    id: "channel-shield",
    title: "Channel Shield and messaging",
    summary: "Inbound protection before mail or chat reaches people or agents.",
    features: [
      {
        id: "channel-shield",
        name: "Channel Shield",
        description:
          "Scan, policy-check, sandbox, quarantine, and summarize inbound email and messaging.",
        usedFor: "Stopping unsafe content before it enters workflows.",
        docsPath: "features/channel-shield",
      },
      {
        id: "messaging",
        name: "Messaging channels",
        description: "Telegram, Discord, Slack, WhatsApp (via providers), webhooks, and personas.",
        usedFor: "Talking to the agent where your team already works.",
        docsPath: "features/messaging",
      },
      {
        id: "voice",
        name: "Voice",
        description: "Voice input, templates, wake words, and receptionist-style flows.",
        usedFor: "Hands-free and phone-adjacent agent use.",
        docsPath: "features/voice",
      },
    ],
  },
  {
    id: "security",
    title: "Security and governance",
    summary: "Vault, ACLs, approvals, tenancy, and optional Scout signals.",
    features: [
      {
        id: "vault",
        name: "Vault and credential proxy",
        description: "Encrypted secrets with injection that keeps credentials out of prompts.",
        usedFor: "Safe tool access to third-party APIs.",
        docsPath: "features/vault",
      },
      {
        id: "review-gateway",
        name: "Review gateway",
        description: "External human review tokens for sensitive actions.",
        usedFor: "Cross-team approval of high-risk work.",
        docsPath: "security/review-gateway",
      },
      {
        id: "tool-acl",
        name: "Tool and resource ACLs",
        description: "Scope which tools and resources each actor can use.",
        usedFor: "Least-privilege agent and operator access.",
        docsPath: "features/tool-acl",
      },
      {
        id: "governance",
        name: "Governance and evidence packs",
        description: "Governance providers, pack gates, and evidence for audits.",
        usedFor: "Regulated or enterprise review trails.",
        docsPath: "features/governance",
      },
      {
        id: "tenant-isolation",
        name: "Multi-tenancy and isolation",
        description: "Workspace and tenant boundaries for memory, CRM, and credentials.",
        usedFor: "Keeping customer data separated.",
        docsPath: "features/tenant-isolation",
      },
      {
        id: "scout",
        name: "Scout / governance connector",
        description: "Optional sanitized signals and control actions to a governance provider.",
        usedFor: "External monitoring without giving up self-hosting.",
        docsPath: "integrations/scout",
      },
    ],
  },
  {
    id: "research",
    title: "Research and data",
    summary: "Deep research, evals, analytics, and model comparison.",
    features: [
      {
        id: "research",
        name: "Deep research",
        description: "Cited research projects with datasets and reproducibility hooks.",
        usedFor: "Long-form investigation with sources.",
        docsPath: "features/research",
      },
      {
        id: "compare-models",
        name: "Compare models",
        description: "Blind A/B evaluation of LLM providers.",
        usedFor: "Choosing models with evidence, not vibes.",
        docsPath: "features/compare-models",
      },
      {
        id: "evals",
        name: "Evals",
        description: "Evaluation cases, traces, and result drawers.",
        usedFor: "Regression testing agent behavior.",
        docsPath: "features/evals",
      },
      {
        id: "analytics",
        name: "Analytics workspace",
        description: "Usage, cost, and operational analytics panels.",
        usedFor: "Understanding spend and agent activity.",
        docsPath: "features/analytics-workspace",
      },
      {
        id: "browser",
        name: "Browser automation",
        description: "Harnessed browser sessions for agent web tasks.",
        usedFor: "Sites that need real browser interaction.",
        docsPath: "features/computer-use-deliverables",
      },
    ],
  },
  {
    id: "integrations",
    title: "Integrations and sidecars",
    summary: "MCP, A2A, universal sidecar, and product packs.",
    features: [
      {
        id: "mcp",
        name: "MCP connectors",
        description: "Model Context Protocol servers as first-class tool sources.",
        usedFor: "Plugging external tools into the agent.",
        docsPath: "features/mcp-connector-first",
      },
      {
        id: "a2a",
        name: "A2A",
        description: "Agent-to-agent provider patterns.",
        usedFor: "Interoperability with other agent runtimes.",
        docsPath: "features/a2a",
      },
      {
        id: "universal-sidecar",
        name: "Universal Sidecar",
        description:
          "Public contract for product sidecars: health, capabilities, pairing, jobs, events, and kill switch.",
        usedFor: "Embedding Keprix beside Clinicom, Fleetz, AbbiS, and other products.",
        docsPath: "universal-sidecar",
      },
      {
        id: "domain-packs",
        name: "Domain packs",
        description: "Installable knowledge and product packs (hub, clinical gates, product sidecars).",
        usedFor: "Sector and product-specific capabilities.",
        docsPath: "features/hub-and-packs",
      },
      {
        id: "sdk",
        name: "SDK",
        description: "Python and TypeScript clients for the App Foundation and APIs.",
        usedFor: "Building on Keprix from other codebases.",
        docsPath: "integrations/sdk",
      },
      {
        id: "google-workspace",
        name: "Google Workspace",
        description: "OAuth-backed Workspace integrations where configured.",
        usedFor: "Mail, calendar, and drive-adjacent workflows.",
        docsPath: "features/agent-sync",
      },
      {
        id: "n8n",
        name: "n8n sidecar",
        description: "Optional n8n alongside Keprix via MCP bridge.",
        usedFor: "Teams that already automate in n8n.",
        docsPath: "integrations/n8n-sidecar",
      },
    ],
  },
  {
    id: "operations",
    title: "Operations and admin",
    summary: "Readiness, billing hooks, quotas, flags, and backups.",
    features: [
      {
        id: "admin-dashboard",
        name: "Admin dashboard",
        description: "Users, tools, channels, mutations, fleet, and readiness.",
        usedFor: "Instance administration.",
        docsPath: "operations/admin-dashboard",
      },
      {
        id: "feature-flags",
        name: "Feature flags and modules",
        description: "Progressive UX flags and module inventory.",
        usedFor: "Rolling out surfaces without breaking the nav.",
        docsPath: "features/feature-flags",
      },
      {
        id: "quotas",
        name: "Quotas and usage",
        description: "Token and usage budgets with operator visibility.",
        usedFor: "Controlling cost per actor or workspace.",
        docsPath: "features/quotas",
      },
      {
        id: "billing",
        name: "Billing hooks",
        description: "Optional Stripe wiring for commercial surfaces; Community stays free.",
        usedFor: "Managed or donation flows without gating OSS.",
        docsPath: "features/billing",
      },
      {
        id: "backup",
        name: "Hot backup",
        description: "Snapshot, verify, and restore archives.",
        usedFor: "Disaster recovery for self-hosted instances.",
        docsPath: "operations/backup",
      },
      {
        id: "localization",
        name: "Localization",
        description: "Corrections and metrics for locale-aware copy.",
        usedFor: "Tuning language for your operators.",
        docsPath: "features/localization",
      },
    ],
  },
];

export const MARKETING_FEATURE_HIGHLIGHTS = [
  {
    id: "tui",
    title: "Command Center TUI",
    body: "Keyboard-first terminal with live sessions, slash commands, tool cards, review mode, and diagnostics.",
    color: "#7c3aed",
  },
  {
    id: "agent-os",
    title: "Agent OS runtime",
    body: "Action boards, run ledgers, agent apps, skills, playbooks, and self-improvement in one secure runtime.",
    color: "#06b6d4",
  },
  {
    id: "channel-shield",
    title: "Channel Shield",
    body: "Scan, quarantine, and summarize inbound email and messaging before agents or people act on it.",
    color: "#10b981",
  },
  {
    id: "crm",
    title: "Agentic CRM",
    body: "Pipeline, discovery, enrichment, outreach, Soft Wall approvals, and Companies House research in-product.",
    color: "#f59e0b",
  },
  {
    id: "memory",
    title: "Memory, Brain, and RAG",
    body: "Long-term recall, knowledge graphs, document pipelines, and self-knowledge about the platform.",
    color: "#ef4444",
  },
  {
    id: "mutation",
    title: "Reviewable self-coding",
    body: "The mutation engine proposes tools and repo changes; you inspect diffs, tests, and risk first.",
    color: "#8b5cf6",
  },
  {
    id: "sidecar",
    title: "Universal Sidecar",
    body: "Embed Keprix beside other products with a public health, pairing, jobs, and kill-switch contract.",
    color: "#0ea5e9",
  },
  {
    id: "vault",
    title: "Vault and Soft Wall",
    body: "Encrypted credentials, ACLs, and approve-then-retry gates for high-risk CRM and mutation actions.",
    color: "#a855f7",
  },
] as const;

export function countMarketingFeatures(): number {
  return MARKETING_FEATURE_CATEGORIES.reduce((n, cat) => n + cat.features.length, 0);
}
