# Admin dashboard

The admin dashboard (`/dashboard`) is the operator console for instance health, users, channels, and mutations.

## Access

Requires `admin` or `owner` role. Linked from chat header **Dashboard** and settings **Instance settings**.

Admins and owners receive the **full curated navigation** (Admin group included). Feature flags and simplified mode do not strip admin nav. See [Navigation and roles](../features/navigation-and-roles.md).

## Sections

| Route | Purpose |
| --- | --- |
| `/dashboard` | Overview metrics, channel health, pending mutations |
| `/dashboard/users` | Invite users, roles, approval |
| `/dashboard/conversations` | Cross-user session audit |
| `/dashboard/mutations` | Approve or reject synthesized tools |
| `/dashboard/tools` | Generated tool catalog |
| `/dashboard/channels` | Telegram, Discord, REST API (theme contrast clamped; see [Theme contrast](../frontend/theme-contrast.md)) |
| `/dashboard/keys` | REST API keys for channels |
| `/dashboard/memory` | Memory index stats |
| `/dashboard/settings` | Instance name, LLM providers, agent behaviour, storage |
| `/admin/feature-flags` | Progressive UI surface toggles ([guide](../features/feature-flags.md)) |
| `/admin/readiness` | Market / upgrade / recovery gates |
| `/admin/upstream` | Hermes release review queue and adoption decisions ([guide](upstream-monitor.md)) |
| `/settings/billing` | Subscription UI plus admin catalog price pins ([guide](../features/billing.md)) |

## LLM providers (dashboard settings)

- Built-in providers: DeepSeek, Anthropic, OpenAI, Gemini, Ollama
- Custom OpenAI-compatible providers
- Set default provider, test connection, remove credentials

Keys persist to the environment file on save.

## Channel health

Overview strip shows Telegram, Discord, and REST status with links to **Channels** configuration.

## API

Admin routes under `/api/admin/*`, `/api/settings/*`, and `/api/billing/admin/*`. See [API reference](../reference/api.md).

## Related

- [Settings](../features/settings.md)
- [Feature flags](../features/feature-flags.md)
- [Billing](../features/billing.md)
- [Readiness](readiness.md)
- [Messaging](../features/messaging.md)
- [Built-in tools](../features/tools.md)
- [Theme contrast](../frontend/theme-contrast.md)
