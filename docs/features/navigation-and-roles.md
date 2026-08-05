# Navigation and roles

The sidebar is a **curated UI contract**, not an auto-list of every Python package or plugin.

Source of truth: `src/keprix/ui_contract/navigation.py` (`NAV_ITEMS`, `navigation_for_role`). The frontend falls back to `frontend/src/lib/navigation.ts` only if the contract is unavailable.

Group order (top to bottom): Workspace → Data → Research → Apps → Installed apps → Automations → Security → Commerce → Admin. Within Admin, Developer is last.

**When adding a menu item:** pick the right group by relevance and place it beside same-type neighbors. Do not invent a new top-level group without an explicit product decision. Update `navigation.py` and the frontend fallback together. Agent rule: `.cursor/rules/keprix-sidebar-nav.mdc`.

## Role policy

| Role | Navigation |
| --- | --- |
| **Admin / owner** | Full curated nav (all groups, including Admin). Simplified mode and feature-flag gates do **not** strip items. |
| **User / operator** | No Admin group. Optional surfaces follow [feature flags](feature-flags.md). Simplified mode (when enabled) further hides advanced routes. |
| **Viewer** | Hides Admin, Commerce, and Automations groups. |

## Progressive disclosure

1. Default work surfaces stay visible for users/operators.
2. Admins turn feature flags on to surface more for those roles.
3. Modules that remain CLI/API-only stay in **Settings → Modules** and **Module inventory**, not necessarily in the sidebar.

This is intentional so the default UX stays usable while the platform remains large.

Curated sidebar entries that are easy to miss in older docs:

| Surface | Route | Group |
| --- | --- | --- |
| Brain | `/brain/graph` | Workspace |
| Memory | `/memory` | Workspace |
| Brain health | `/brain/health` | Data |
| A2A | `/a2a` | Automations |
| Observability | `/observability` | Data |
| Developer | `/developer` | Admin (last) |

Modules catalog statuses (`available`, `partial`, `cli_api`) are defined in `src/keprix/upgrade/gui_catalog.py`. See [Settings](settings.md).

## Diagnostics

| Surface | Route |
| --- | --- |
| Modules catalog | `/settings/modules` |
| Module inventory | `/developer/module-inventory` |
| UI contract | `GET /api/ui/contract` |

## Related

- [Feature flags](feature-flags.md)
- [Brain graph](brain.md)
- [A2A](a2a.md)
- [Built apps navigation](built-apps-navigation.md)
- [Agent OS client kit](agent-os-client-kit.md)
- [Settings](settings.md)
