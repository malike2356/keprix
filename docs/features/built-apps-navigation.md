# Built apps navigation

Built apps use a two-layer navigation model. The Keprix platform sidebar stays focused on workspace tools, while each installed product owns its own navigation inside the content area.

## Overview

The platform sidebar answers where the user is in Keprix. Built app navigation answers where the user is inside a product hosted by Keprix.

| Layer | Location | Responsibility |
| --- | --- | --- |
| Platform sidebar | Left pane | Workspace, apps, research, automation, security, admin, and one entry per installed built app |
| Built app shell | Main content | App header, breadcrumbs, app sections, optional sub-rail, and app pages |

Routes under `/apps/[slug]/*` still use the normal workspace `AppShell`, so Chat, Home, Settings, and other platform areas remain reachable.

## For operators

Installed apps appear under the **Installed apps** sidebar group. Each app appears once, using the app label and entry route from its manifest.

The sidebar groups are collapsible. Workspace opens by default, and Installed apps opens automatically when the active route is under `/apps/`.

To install the starter manifest in development:

```bash
mkdir -p "$KEPRIX_DATA_DIR/built_apps/starter"
cp examples/built-app-starter/built_app.yaml "$KEPRIX_DATA_DIR/built_apps/starter/"
```

After restart or contract refresh, the starter app is available at `/apps/starter`.

## For app builders

Create a `built_app.yaml` file in:

```text
$KEPRIX_DATA_DIR/built_apps/{id}/built_app.yaml
```

Required fields:

```yaml
id: starter
label: Starter app
entry: /apps/starter
navigation:
  style: sections
  items:
    - id: dashboard
      label: Dashboard
      href: /apps/starter
```

Rules:

| Field | Rule |
| --- | --- |
| `id` | Letters, numbers, hyphens, and underscores |
| `entry` | Must start with `/apps/{id}` |
| `navigation.items[].href` | Must start with `/apps/{id}` |
| `navigation.style` | `sections`, `sub_rail`, or `tabs_only` |

Use `BuiltAppLayout` from `frontend/src/components/built-app/` to render the in-content shell.

## Inner nav patterns

| Pattern | Use when |
| --- | --- |
| `sections` | The app has peer areas such as Dashboard, Reports, Settings |
| `sub_rail` | The app has deeper modules that benefit from a left sub-navigation column |
| `tabs_only` | The app wants to render its own page-level tabs and only needs the header shell |

## Agent Apps vs built apps

| Surface | Use for |
| --- | --- |
| `/agent-apps` | Runnable agent workflows, forms, schedules, webhooks, and installable automations |
| `/apps/[slug]` | Full product UIs hosted inside the Keprix workspace |

An app can expose both. Keep the product UI under `/apps/[slug]` and any runnable workflow package under Agent Apps.

## AbbiS note

AbbiS product UI should live outside Keprix core in `verlox/apps-on-keprix/abbis/`. It can copy the starter manifest and use Keprix shell primitives, but AbbiS-specific routes should not be added to core `navigation.py`.

## Related

- [Navigation and roles](navigation-and-roles.md)
- [Feature flags](feature-flags.md)

## Troubleshooting

| Symptom | Check |
| --- | --- |
| App missing from sidebar | Confirm `KEPRIX_DATA_DIR/built_apps/{id}/built_app.yaml` exists and the backend can read it |
| Manifest rejected | Confirm `entry` and every inner `href` start with `/apps/{id}` |
| Inner tab not active | Confirm the browser path exactly matches or is nested under the nav item `href` |
| Sidebar group collapsed | Expand Installed apps or open any `/apps/` route |

## Manual QA

| Check | Pass |
| --- | --- |
| Collapsible platform groups | |
| Starter app in Installed apps | |
| Inner section nav on `/apps/starter` | |
| Chat reachable without leaving Keprix shell | |
