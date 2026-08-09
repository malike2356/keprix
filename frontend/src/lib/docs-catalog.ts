import { DOCS_HOME_URL, DOCS_QUICKSTART_URL, docsPageUrl } from "@/lib/docs-url";

export type DocsSection = {
  title: string;
  description: string;
  items: Array<{ title: string; description: string; href: string }>;
};

function doc(path: string): string {
  return docsPageUrl(path);
}

export const DOCS_SECTIONS: DocsSection[] = [
  {
    title: "Getting started",
    description: "Install, first run, and developer mode.",
    items: [
      { title: "Quickstart", description: "Docker install in under five minutes.", href: DOCS_QUICKSTART_URL },
      { title: "Manual install", description: "Bare metal and custom deployments.", href: doc("getting-started/manual-install") },
      { title: "Cloud deploy", description: "VPS and cloud checklist.", href: doc("getting-started/cloud-deploy") },
      { title: "First run", description: "Setup wizard and health checks.", href: doc("getting-started/first-run") },
      { title: "Authentication", description: "Login, register, roles, onboarding.", href: doc("getting-started/authentication") },
      { title: "Developer mode", description: "Local identity and API keys.", href: doc("getting-started/developer-mode") },
    ],
  },
  {
    title: "Configuration",
    description: "Environment, providers, and Compose.",
    items: [
      { title: "Environment variables", description: "Full .env reference.", href: doc("configuration/environment-variables") },
      { title: "Docker Compose", description: "Service layout and volumes.", href: doc("configuration/docker-compose") },
      { title: "LLM providers", description: "Built-in and custom OpenAI-compatible endpoints.", href: doc("configuration/llm-providers") },
      { title: "Developer identity", description: "Fingerprint and machine owner.", href: doc("configuration/developer-identity") },
    ],
  },
  {
    title: "Workspace",
    description: "Day-to-day tools in the web UI.",
    items: [
      { title: "Workspace overview", description: "Home, navigation, and data model.", href: doc("features/workspace") },
      { title: "Chat", description: "Sessions, models, tools, slash commands.", href: doc("features/chat") },
      { title: "Documents", description: "Files, uploads, and exports.", href: doc("features/documents") },
      { title: "Notes", description: "Linked notes and references.", href: doc("features/notes") },
      { title: "Tasks", description: "To-do, in progress, and done.", href: doc("features/tasks") },
      { title: "Calendar", description: "Month, week, day, and schedule views.", href: doc("features/calendar") },
      { title: "Email", description: "IMAP inbox, AI triage, send API.", href: doc("features/email") },
      { title: "Contacts", description: "People, sync, and preferences.", href: doc("features/contacts") },
      { title: "Gallery", description: "Generated and uploaded images.", href: doc("features/gallery") },
      { title: "Memory", description: "Long-term recall and RAG.", href: doc("features/memory") },
      { title: "Settings", description: "Workspace and instance configuration.", href: doc("features/settings") },
    ],
  },
  {
    title: "Apps and research",
    description: "Skills, packs, research, and go-to-market.",
    items: [
      { title: "Skills and plugins", description: "Skills Hub and extensions.", href: doc("features/skills") },
      { title: "Hub and domain packs", description: "Install packs and clinical gates.", href: doc("features/hub-and-packs") },
      { title: "Deep research", description: "Cited research projects.", href: doc("features/research") },
      { title: "Compare models", description: "Blind A/B evaluation.", href: doc("features/compare-models") },
      { title: "Opportunity engine", description: "Market research and launch playbooks.", href: doc("opportunity-engine") },
      { title: "Local models", description: "Hardware scan and Ollama.", href: doc("features/local-models") },
      { title: "Agentic CRM", description: "Pipeline, discovery, outreach, Soft Wall.", href: doc("features/agentic-crm") },
      { title: "Companies House", description: "UK company lookup and enrichment.", href: doc("features/companies-house") },
      { title: "Vical booking", description: "Public booking with Soft Wall enroll.", href: doc("features/vical") },
      { title: "Soft Wall", description: "Approve-then-retry for high-risk outbound.", href: doc("features/soft-wall-safety") },
    ],
  },
  {
    title: "Troubleshooting and help",
    description: "Fix dead clicks, outreach Soft Wall, CRM, Companies House, and RAG answers.",
    items: [
      { title: "Troubleshooting hub", description: "Symptom → cause → fix for every major surface.", href: doc("troubleshooting") },
      { title: "UI navigation", description: "Tabs and cards that do not open pages.", href: doc("troubleshooting/ui-navigation") },
      { title: "Soft Wall and outreach", description: "Approvals, pause, deliverability, channels.", href: doc("troubleshooting/soft-wall-and-outreach") },
      { title: "Agentic CRM help", description: "Discover, enrich, enroll, jobs stuck.", href: doc("troubleshooting/agentic-crm") },
      { title: "Companies House help", description: "API key and empty search results.", href: doc("troubleshooting/companies-house") },
      { title: "Self-knowledge RAG", description: "Re-index when the agent does not know Keprix.", href: doc("troubleshooting/self-knowledge") },
      { title: "Known issues", description: "Dated defects and fixed regressions.", href: doc("troubleshooting/known-issues") },
    ],
  },
  {
    title: "Automations",
    description: "Agents, cron, coding, and tool synthesis.",
    items: [
      { title: "Agent", description: "Runtime, tools, and mutation engine.", href: doc("features/agent") },
      { title: "Self-coding agent", description: "Long-horizon coding sessions.", href: doc("features/self-coding-agent") },
      { title: "Playbooks", description: "YAML automation workflows.", href: doc("features/playbooks") },
      { title: "Cron jobs", description: "Scheduled agent tasks.", href: doc("features/cron-jobs") },
      { title: "Built-in tools", description: "Tool catalog and approvals.", href: doc("features/tools") },
      { title: "Agent Studio", description: "Build and publish agent apps.", href: doc("features/agent-studio") },
      { title: "Agent Apps", description: "Install, run, and schedule manifest-driven apps.", href: doc("features/agent-apps") },
      { title: "MCP servers", description: "External tool connectors.", href: doc("integrations/mcp") },
      { title: "n8n sidecar", description: "Run n8n alongside Keprix via MCP bridge.", href: doc("integrations/n8n-sidecar") },
      { title: "Universal Sidecar", description: "Product sidecar health, pairing, jobs, kill switch.", href: doc("universal-sidecar") },
      { title: "Propreneur sidecar", description: "Property MIS bridge, auth, canary, rollback.", href: doc("propreneur-sidecar") },
      { title: "Channel Shield", description: "Inbound email and messaging protection.", href: doc("features/channel-shield") },
    ],
  },
  {
    title: "Security and admin",
    description: "Vault, governance, dashboard, and developer API.",
    items: [
      { title: "Security architecture", description: "Trust boundaries.", href: doc("security/architecture") },
      { title: "Vault", description: "Encrypted credentials.", href: doc("security/vault") },
      { title: "Governance", description: "Governance providers, evidence packs, and pack gate.", href: doc("security/governance") },
      { title: "Review gateway", description: "External reviewer tokens.", href: doc("security/review-gateway") },
      { title: "Hardening", description: "Production checklist.", href: doc("security/hardening") },
      { title: "Admin dashboard", description: "Users, channels, mutations.", href: doc("operations/admin-dashboard") },
      { title: "Developer platform", description: "API keys, webhooks, OpenAPI.", href: doc("features/developer-platform") },
      { title: "Notifications", description: "Inbox, digests, external SMTP.", href: doc("features/notifications") },
    ],
  },
  {
    title: "Integrations and reference",
    description: "APIs, SDK, and auto-generated reference.",
    items: [
      { title: "OpenAI-compatible API", description: "/v1/chat/completions and more.", href: doc("integrations/openai-api") },
      { title: "SDK", description: "Python and TypeScript clients.", href: doc("integrations/sdk") },
      { title: "Governance integrations", description: "Optional governance provider connectors.", href: doc("integrations/scout") },
      { title: "REST API reference", description: "Auto-generated from OpenAPI.", href: doc("reference/api") },
      { title: "CLI reference", description: "Auto-generated from keprix --help.", href: doc("reference/cli") },
    ],
  },
  {
    title: "Operations",
    description: "Backup, data planes, and production runbooks.",
    items: [
      { title: "Hot backup", description: "Snapshot, verify, and restore archives.", href: doc("operations/backup") },
      { title: "Data planes", description: "Four-plane storage and job architecture.", href: doc("operations/data-planes") },
      { title: "Admin dashboard", description: "Users, channels, mutations, and fleet.", href: doc("operations/admin-dashboard") },
      { title: "Cloud deploy", description: "VPS and production checklist.", href: doc("getting-started/cloud-deploy") },
      { title: "Hardening", description: "Production security checklist.", href: doc("security/hardening") },
      { title: "Privacy centre", description: "GDPR, retention, and erasure.", href: doc("security/privacy") },
    ],
  },
  {
    title: "Community",
    description: "Contribute, publish packs, and join discussions.",
    items: [
      { title: "Contributing", description: "Fork, branch, test, and open a PR.", href: doc("community/contributing") },
      { title: "Code of conduct", description: "Community standards and enforcement.", href: doc("community/code-of-conduct") },
      { title: "Domain packs", description: "Author and submit knowledge packs.", href: doc("community/packs") },
      { title: "Good first issues", description: "Starter tasks for new contributors.", href: doc("community/good-first-issues") },
      { title: "Issue labels", description: "How we triage and prioritize work.", href: doc("community/labels") },
      { title: "Discussions", description: "Questions, ideas, and show-and-tell.", href: doc("community/discussions") },
    ],
  },
];

export const DOCS_GITHUB_EDIT_URL = "https://github.com/malike2356/keprix/tree/main/docs";
export { DOCS_HOME_URL };
