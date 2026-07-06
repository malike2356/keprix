# Admin dashboard

The admin dashboard (`/dashboard`) is the operator console for instance health, users, channels, and mutations.

## Access

Requires `admin` or `owner` role. Linked from chat header **Dashboard** and settings **Instance settings**.

## Sections

| Route | Purpose |
| --- | --- |
| `/dashboard` | Overview metrics, channel health, pending mutations |
| `/dashboard/users` | Invite users, roles, approval |
| `/dashboard/conversations` | Cross-user session audit |
| `/dashboard/mutations` | Approve or reject synthesized tools |
| `/dashboard/tools` | Generated tool catalog |
| `/dashboard/channels` | Telegram, Discord, REST API |
| `/dashboard/keys` | REST API keys for channels |
| `/dashboard/memory` | Memory index stats |
| `/dashboard/settings` | Instance name, LLM providers, agent behaviour, storage |

## LLM providers (dashboard settings)

- Built-in providers: DeepSeek, Anthropic, OpenAI, Gemini, Ollama
- Custom OpenAI-compatible providers
- Set default provider, test connection, remove credentials

Keys persist to the environment file on save.

## Channel health

Overview strip shows Telegram, Discord, and REST status with links to **Channels** configuration.

## API

Admin routes under `/api/admin/*` and `/api/settings/*`. See [API reference](../reference/api.md).

## Related

- [Settings](../features/settings.md)
- [Messaging](../features/messaging.md)
- [Built-in tools](../features/tools.md)
