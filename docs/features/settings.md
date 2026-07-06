# Settings

Keprix has two settings layers: **workspace settings** for every signed-in user, and **instance settings** (admin dashboard) for operators.

## Workspace settings (`/settings`)

Hub page with cards linking to specialized areas.

| Card | Route | Purpose |
| --- | --- | --- |
| Vault | `/vault` | Encrypted passwords and API tokens |
| Cron jobs | `/admin/cron` | Scheduled agent tasks |
| MCP servers | `/admin/mcp` | External tool servers; Notion/Trello catalog, OAuth, skills/RAG fallbacks ([guide](../integrations/productivity-notion-trello.md)) |
| Backup | `/admin/backup` | Export and restore |
| Developer platform | `/developer` | API keys and webhooks |
| Privacy | `/privacy` | Consent, DSAR, erasure |
| Voice templates | `/settings/voice-templates` | Pre-recorded TTS phrases |
| Localization | `/settings/localization/*` | Corrections and metrics (admin) |
| Browser harness | `/settings/browser` | Agent browser sessions |
| Pack gate | `/settings/pack-gate` | Clinical sign-off (admin) |
| Notifications | `/settings/notifications` | Channels, quiet hours, digests |
| External notifications | `/settings/notifications/external` | SMTP to reviewers (admin) |
| Evidence packs | `/settings/governance/evidence-packs` | Signed archives (admin) |
| Governance | `/settings/governance` | Labyrinth Scout connector |
| Instance settings | `/dashboard/settings` | LLM providers, agent behaviour (admin) |

### Appearance

The **Appearance** row opens a compact theme picker (light/dark mode and color skins). Preference is stored in the browser.

## Instance settings (`/dashboard/settings`)

Admin-only tabs:

| Tab | Configures |
| --- | --- |
| General | Instance name, URL, timezone, language |
| LLM Providers | Built-in and custom OpenAI-compatible providers |
| Agent behaviour | Tool iterations, context compression, mutation engine |
| Storage | Postgres, Redis, vector store, memory limits |
| Scout connector | License key and audit policy (when enabled) |

Provider API keys are written to the environment file on save. Custom providers support Ollama, LM Studio, vLLM, RunPod, and similar endpoints.

## Messaging settings (`/settings/messaging`)

Ambient monitoring for group channels (WhatsApp, Telegram groups, etc.). Not the same as email IMAP accounts.

## Notification preferences (`/settings/notifications`)

Per-channel toggles (in-app, email, push), quiet hours, digest email, and approval escalation timing.

## Governance (`/settings/governance`)

Connect **Labyrinth Scout** for kill switches, audit trails, and policy enforcement. Scout requires a separate license from [labyrinthscout.com](https://labyrinthscout.com). keprix stores the API key encrypted; it does not sell Scout subscriptions in-app.

## API

Workspace and admin settings routes are under `/api/settings/*` and `/api/admin/*`. See [API reference](../reference/api.md).

## Related

- [LLM providers](../configuration/llm-providers.md)
- [Admin dashboard](../operations/admin-dashboard.md)
- [Governance](../security/governance.md)
- [Notifications](notifications.md)
