# Keprix Documentation

Keprix is a self-hosted AI agent OS (Community Edition). You run it on your own hardware; your data stays under your control.

This site is the complete operator and developer reference for every workspace surface, admin tool, integration, and API.

## Start here

| I want to... | Read |
| --- | --- |
| Understand the full product | [Full product map](features/full-product-map.md) |
| Install in five minutes | [Quickstart](getting-started/quickstart.md) |
| Complete the setup wizard | [First run](getting-started/first-run.md) |
| Configure `.env` and providers | [Environment variables](configuration/environment-variables.md), [LLM providers](configuration/llm-providers.md) |
| Use chat, tools, and the terminal Command Center | [Chat](features/chat.md), [Terminal UI](features/tui.md), [TUI slash commands](reference/tui-slash.md) |
| Configure the instance | [Settings](features/settings.md), [Admin dashboard](operations/admin-dashboard.md) |
| Protect inbound channels | [Channel Shield](features/channel-shield.md) |
| Call the REST API | [API reference](reference/api.md), [Developer platform](features/developer-platform.md) |
| Harden production | [Hardening](security/hardening.md) |

## Product map

### Workspace (daily use)

| Area | Route | Documentation |
| --- | --- | --- |
| Home | `/home` | [Workspace overview](features/workspace.md) |
| Chat | `/chat` | [Chat](features/chat.md), [Web voice input](features/web-voice-input.md) |
| Terminal Command Center | `keprix tui` | [Terminal UI](features/tui.md), [TUI slash commands](reference/tui-slash.md) |
| Documents | `/documents` | [Documents](features/documents.md) |
| Notes | `/notes` | [Notes](features/notes.md) |
| Tasks | `/tasks` | [Tasks](features/tasks.md) |
| Calendar | `/calendar` | [Calendar](features/calendar.md) |
| Email | `/email` | [Email](features/email.md) |
| Contacts | `/contacts` | [Contacts](features/contacts.md) |
| Gallery | `/gallery` | [Gallery](features/gallery.md) |
| Brain | `/brain/graph` | [Brain graph](features/brain.md) |
| Memory (list) | `/memory` | [Memory and RAG](features/memory.md) |
| Settings | `/settings` | [Settings](features/settings.md) |
| Billing | `/settings/billing` | [Billing](features/billing.md) |

### Apps, research, and data

| Area | Route | Documentation |
| --- | --- | --- |
| Skills Hub | `/skills` | [Skills and plugins](features/skills.md) |
| Hub / packs | `/hub`, `/domain-packs` | [Hub and domain packs](features/hub-and-packs.md) |
| Built apps | `/apps/[slug]` | [Built apps navigation](features/built-apps-navigation.md) |
| Deep research | `/research` | [Research](features/research.md) |
| Compare models | `/compare` | [Compare models](features/compare-models.md) |
| Opportunities | `/opportunities` | [Opportunity engine](opportunity-engine.md) |
| Local models | `/playbook` | [Local models](features/local-models.md) |
| Analytics | `/analytics` | [Analytics workspace](features/analytics-workspace.md) |
| Observability | `/observability` | [Evals and observability](features/evals.md) |
| Notebook research | `/research/notebooks` | [Notebook research bridge](features/notebook-research-bridge.md) |

### Automations and agent runtime

| Area | Route | Documentation |
| --- | --- | --- |
| Agent chat runtime | (via `/chat`) | [Agent](features/agent.md) |
| Self-coding | `/admin/coding` | [Self-coding agent](features/self-coding-agent.md) |
| Playbooks | `/playbooks` | [Playbooks](features/playbooks.md) |
| Cron jobs | `/admin/cron` | [Cron jobs](features/cron-jobs.md) |
| Tools | `/admin/tools` | [Built-in tools](features/tools.md) |
| Agent OS | `/agent-os` | [Agent OS overview](features/agent-os-overview.md), [Run ledger](features/agent-os-run-ledger.md) |
| Agent Studio | `/agent-studio` | [Agent Studio](features/agent-studio.md) |
| Agent Apps | `/agent-apps` | [Agent Apps](features/agent-apps.md) |
| A2A | `/a2a` | [A2A](features/a2a.md) |
| MCP | `/admin/mcp` | [MCP](integrations/mcp.md), [Notion & Trello](integrations/productivity-notion-trello.md) |
| Control Center | `/control-center` | [Control Center](features/control-center.md) |

### Security, governance, admin

| Area | Route | Documentation |
| --- | --- | --- |
| Vault | `/vault` | [Vault](security/vault.md) |
| Governance | `/settings/governance` | [Governance](security/governance.md) |
| Review gateway | `/review-gateway` | [Review gateway](security/review-gateway.md) |
| Channel Shield | `/channel-shield`, `/settings/channel-shield` | [Channel Shield](features/channel-shield.md) |
| Admin dashboard | `/dashboard` | [Admin dashboard](operations/admin-dashboard.md) |
| Feature flags | `/admin/feature-flags` | [Feature flags](features/feature-flags.md) |
| Navigation policy | (sidebar) | [Navigation and roles](features/navigation-and-roles.md) |
| Readiness | `/admin/readiness` | [Readiness](operations/readiness.md) |
| Developer | `/developer` | [Developer platform](features/developer-platform.md) |
| Notifications | `/notifications` | [Notifications](features/notifications.md) |

## Health checks

```bash
curl -s http://127.0.0.1:3333/api/health
```

- Backend API: `http://localhost:3333`
- Web UI: `http://localhost:3000`
- Interactive API explorer: `http://localhost:3000/api/docs`
- MkDocs (local): `bash scripts/serve-docs.sh` then `http://127.0.0.1:8000`

## Support

- [GitHub Issues](https://github.com/malike2356/keprix/issues) for bugs
- [GitHub Discussions](https://github.com/malike2356/keprix/discussions) for questions
- [Contributing](community/contributing.md) for PR workflow
