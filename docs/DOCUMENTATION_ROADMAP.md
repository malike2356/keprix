# Documentation roadmap

This file tracks coverage of every Keprix product surface. Status keys:

| Status | Meaning |
| --- | --- |
| **Complete** | Operator guide with UI, API, config, and troubleshooting |
| **Draft** | Substantive content; may need screenshots or edge cases |
| **Stub** | Outline or route table only |
| **Missing** | No dedicated page yet |

Last updated: 2026-07-06

## Getting started

| Page | Path | Status |
| --- | --- | --- |
| Home | `index.md` | Draft |
| Quickstart | `getting-started/quickstart.md` | Draft |
| Manual install | `getting-started/manual-install.md` | Draft |
| Cloud deploy | `getting-started/cloud-deploy.md` | Draft |
| First run | `getting-started/first-run.md` | Draft |
| Developer mode | `getting-started/developer-mode.md` | Draft |
| Authentication | `getting-started/authentication.md` | Draft |

## Configuration

| Page | Path | Status |
| --- | --- | --- |
| Environment variables | `configuration/environment-variables.md` | Complete |
| Docker Compose | `configuration/docker-compose.md` | Draft |
| LLM providers | `configuration/llm-providers.md` | Draft |
| Developer identity | `configuration/developer-identity.md` | Stub |

## Workspace features

| Surface | Route | Path | Status |
| --- | --- | --- | --- |
| Home / launcher | `/launcher` | `features/workspace.md` | Draft |
| Chat | `/chat` | `features/chat.md` | Draft |
| Documents | `/documents` | `features/documents.md` | Draft |
| Notes | `/notes` | `features/notes.md` | Draft |
| Tasks | `/tasks` | `features/tasks.md` | Draft |
| Calendar | `/calendar` | `features/calendar.md` | Draft |
| Email | `/email` | `features/email.md` | Draft |
| Contacts | `/contacts` | `features/contacts.md` | Draft |
| Gallery | `/gallery` | `features/gallery.md` | Draft |
| Memory | `/memory` | `features/memory.md` | Stub |
| Settings hub | `/settings` | `features/settings.md` | Draft |

## Apps and packs

| Surface | Route | Path | Status |
| --- | --- | --- | --- |
| Skills Hub | `/skills` | `features/skills.md` | Stub |
| Hub | `/hub` | `features/hub-and-packs.md` | Draft |
| Domain packs | `/domain-packs` | `features/hub-and-packs.md` | Draft |
| Project Builder | `/builder` | `features/project-builder.md` | Missing |
| Migrate | `/migrate` | `features/migration.md` | Missing |
| Agent Studio | `/agent-studio` | `features/agent-studio.md` | Stub |
| Agent Apps | `/agent-apps` | `features/agent-apps.md` | Complete |

## Research and evaluation

| Surface | Route | Path | Status |
| --- | --- | --- | --- |
| Deep Research | `/research` | `features/research.md` | Stub |
| Research workspace | `/research` | `research/research-workspace-architecture.md` | Draft (orphan) |
| Compare models | `/compare` | `features/compare-models.md` | Draft |
| Opportunity engine | `/opportunities` | `opportunity-engine.md` | Complete (orphan) |
| Evals | `/evals` | `features/evals.md` | Stub (orphan) |

## Data and local models

| Surface | Route | Path | Status |
| --- | --- | --- | --- |
| Local models | `/playbook` | `features/local-models.md` | Draft |
| RAG pipelines | `/rag-pipeline` | `features/rag-pipelines.md` | Missing |
| Analytics workspace | `/analytics` | `features/analytics-workspace.md` | Stub (orphan) |

## Automations

| Surface | Route | Path | Status |
| --- | --- | --- | --- |
| Playbooks | `/playbooks` | `features/playbooks.md` | Stub (orphan) |
| Agent Teams | `/admin/teams` | `features/agent-teams.md` | Stub (orphan) |
| Agent Runtime | `/agent-runtime` | `features/agent-runtime.md` | Missing |
| Control Center | `/control-center` | `features/control-center.md` | Missing |
| Cron jobs | `/admin/cron` | `features/cron-jobs.md` | Draft |
| Coding workspace | `/admin/coding` | `features/self-coding-agent.md` | Stub |
| Tools admin | `/admin/tools` | `features/tools.md` | Stub |
| Browser automation | `/settings/browser` | `features/browser-automation.md` | Stub (orphan) |
| MCP servers | `/admin/mcp` | `integrations/mcp.md` | Draft |

## Security and governance

| Surface | Route | Path | Status |
| --- | --- | --- | --- |
| Vault | `/vault` | `security/vault.md` | Draft |
| Review gateway | `/review-gateway` | `security/review-gateway.md` | Draft |
| Governance / Scout | `/settings/governance` | `security/governance.md` | Draft |
| Pack gate | `/settings/pack-gate` | `security/governance.md` | Draft |
| Privacy / DSAR | `/privacy` | `security/privacy.md` | Missing |
| Support | `/support` | `features/support.md` | Missing |

## Notifications and voice

| Surface | Route | Path | Status |
| --- | --- | --- | --- |
| Messaging channels | Telegram, Discord, REST | `features/messaging.md` | Stub |
| Web notifications | `/notifications` | `features/notifications.md` | Draft |
| External SMTP notify | `/settings/notifications/external` | `features/notifications.md` | Draft |
| Voice templates | `/settings/voice-templates` | `features/voice.md` | Missing |
| Localization | `/settings/localization` | `features/localization.md` | Missing |

## Admin and developer

| Surface | Route | Path | Status |
| --- | --- | --- | --- |
| Admin dashboard | `/dashboard` | `operations/admin-dashboard.md` | Draft |
| Developer platform | `/developer` | `features/developer-platform.md` | Draft |
| OpenAPI explorer | `/api/docs` | `integrations/openai-api.md` | Partial |

## Integrations

| Integration | Path | Status |
| --- | --- | --- |
| MCP | `integrations/mcp.md` | Draft |
| ACP | `integrations/acp.md` | Stub |
| Mobile | `integrations/mobile.md` | Draft |
| SDK | `integrations/sdk.md` | Stub |
| OpenAI-compatible API | `integrations/openai-api.md` | Draft |
| Scout | `integrations/scout.md` | Draft |
| Petraclus | `integrations/petraclus.md` | Stub |

## Reference (auto-generated)

| Page | Path | Status |
| --- | --- | --- |
| REST API | `reference/api.md` | Complete |
| CLI | `reference/cli.md` | Complete |
| Changelog | `reference/changelog.md` | Draft |
| License | `reference/license.md` | Draft |

## How to contribute to docs

1. Edit markdown under `docs/`.
2. Add the page to `mkdocs.yml` nav if it should appear on the site.
3. Update this roadmap status.
4. Run `bash scripts/build-docs.sh` and `pytest tests/docs/`.
5. Mirror new sections in `frontend/src/lib/docs-catalog.ts` for the `/docs` portal.
