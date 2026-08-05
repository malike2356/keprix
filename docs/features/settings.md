# Settings

Keprix has two settings layers: **workspace settings** for every signed-in user, and **instance settings** (admin dashboard) for operators.

## Workspace settings (`/settings`)

Hub page with cards linking to specialized areas.

| Card | Route | Purpose |
| --- | --- | --- |
| Billing | `/settings/billing` | Plans, wallet, Stripe portal; admin pricing pins ([guide](billing.md)) |
| Modules | `/settings/modules` | Catalog of packages beyond the sidebar (`available` / `partial` / `cli_api`) |
| Vault | `/vault` | Encrypted passwords and API tokens |
| Cron jobs | `/admin/cron` | Scheduled agent tasks |
| MCP servers | `/admin/mcp` | External tool servers; Notion/Trello catalog, OAuth, skills/RAG fallbacks ([guide](../integrations/productivity-notion-trello.md)) |
| Backup | `/admin/backup` | Export and restore |
| Developer platform | `/developer` | API keys and webhooks; module inventory |
| Privacy | `/privacy` | Consent, DSAR, erasure |
| Voice templates | `/settings/voice-templates` | Pre-recorded TTS phrases |
| Localization | `/settings/localization/*` | Corrections and metrics (admin) |
| Browser harness | `/settings/browser` | Agent browser sessions |
| Pack gate | `/settings/pack-gate` | Clinical sign-off (admin) |
| Notifications | `/settings/notifications` | Channels, quiet hours, digests |
| External notifications | `/settings/notifications/external` | SMTP to reviewers (admin) |
| Evidence packs | `/settings/governance/evidence-packs` | Signed archives (admin) |
| Governance | `/settings/governance` | Labyrinth Scout connector |
| Feature flags | `/admin/feature-flags` | Progressive UI surfaces (admin; [guide](feature-flags.md)) |
| Instance settings | `/dashboard/settings` | LLM providers, agent behaviour (admin) |

### Modules catalog statuses

Source: `src/keprix/upgrade/gui_catalog.py` via `GET /api/keprix/upgrade/modules` (and the UI module inventory).

| Status | Meaning |
| --- | --- |
| `available` | Dedicated GUI route exists and is linked from the catalog |
| `partial` | Some UI exists, but the surface is incomplete |
| `cli_api` | CLI or API only; no first-class page |

Examples marked `available`: SSO (`/settings/account/connected-accounts`), Notion (`/integrations?id=notion`), A2A (`/a2a`), Observability (`/observability`). Restart the API process after catalog code changes; a stale uvicorn process can keep reporting old `partial` counts.

### Appearance

Theme preference is stored in the browser. Exact controls depend on the active frontend shell. Skin accents are contrast-clamped for buttons and body text; see [Theme contrast](../frontend/theme-contrast.md).

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

- [Billing](billing.md)
- [Feature flags](feature-flags.md)
- [Navigation and roles](navigation-and-roles.md)
- [A2A](a2a.md)
- [Evals and observability](evals.md)
- [LLM providers](../configuration/llm-providers.md)
- [Admin dashboard](../operations/admin-dashboard.md)
- [Governance](../security/governance.md)
- [Notifications](notifications.md)
- [Theme contrast](../frontend/theme-contrast.md)
