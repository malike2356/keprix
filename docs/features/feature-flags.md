# Feature flags

Runtime switches for **progressive user and operator UI surfaces**. They are not a full inventory of every Keprix backend package, plugin, or CLI module.

## Who sees what

| Role | Behaviour |
| --- | --- |
| **Admin / owner** | Full curated navigation. Feature flags do **not** hide admin nav. |
| **User / operator** | Work surfaces only (no Admin group). Flags can hide or reveal optional modules. |
| **Viewer** | Narrower set (no Admin, Commerce, Automations groups). |

Canonical nav contract: `src/keprix/ui_contract/navigation.py`. Flag-to-nav gates live in `FLAG_NAV_GATES`.

## Admin UI

Open **`/admin/feature-flags`**.

- Toggle flags on or off (takes effect on the next UI contract request; no restart)
- Reset one flag or all overrides
- **Grid** (multi-column) or **list** view; preference stored in the browser
- Overrides persist in `~/.keprix/feature_flags.json`

## What flags cover

Roughly a dozen progressive surfaces, for example:

- Workspace: research, playbooks, calendar, email, contacts, data workspace, opportunity engine
- Apps: agent apps, builder, browser
- Developer: evals, coding
- Interface: voice input, simplified mode
- Security / admin: governance, commerce (billing UI for non-admins)

For the wider catalog (CLI/API-only modules, plugins, unlinked pages), use:

- **Settings → Modules** (`/settings/modules`)
- **Developer → Module inventory** (`/developer/module-inventory`)

Modules statuses are `available`, `partial`, or `cli_api`. SSO, Notion, A2A (`/a2a`), and Observability (`/observability`) are catalogued as `available`. See [Settings](settings.md).
## API

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/admin/feature-flags` | List flags with effective and override state |
| `PATCH` | `/api/admin/feature-flags/{id}` | Set `{ "enabled": true\|false }` |
| `DELETE` | `/api/admin/feature-flags/{id}` | Clear override |
| `POST` | `/api/admin/feature-flags/reset-all` | Clear all overrides |
| `GET` | `/api/ui/contract` | Includes `feature_flags` and role-filtered `navigation` |

Admin/owner only for mutation routes.

## Related

- [Navigation and roles](navigation-and-roles.md)
- [Settings](settings.md)
- [Admin dashboard](../operations/admin-dashboard.md)
- [Agent OS client kit](agent-os-client-kit.md) (simplified mode)
