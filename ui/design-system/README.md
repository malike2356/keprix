# Keprix design system

Unified UI/UX for web, mobile, desktop, TUI, CLI, and embedded apps (Prompt 22).

## Principles

- One product language: terminology, status labels, navigation groups, and approval patterns are shared across surfaces.
- Professional, calm, premium: restrained color, compact radius (8px or less), no decorative gradients in product UI.
- Contract-first: clients consume `/api/ui/contract` and `ui/design-system/tokens/` rather than inventing per-surface copy.

## Tokens

| File | Purpose |
| --- | --- |
| `tokens/colors.json` | Light and dark semantic palettes |
| `tokens/typography.json` | Font families, sizes, weights |
| `tokens/spacing.json` | 4px step scale |
| `tokens/radius.json` | Border radius steps |
| `tokens/shadows.json` | Elevation shadows |
| `tokens/motion.json` | Duration and easing for state changes |
| `tokens/status.json` | Shared status vocabulary |
| `tokens/icons.json` | Icon name registry for navigation and actions |

Frontend imports tokens from `frontend/src/theme/tokens/`. Backend mirrors status labels in `src/keprix/ui_contract/statuses.py`.

## Navigation groups

1. Workspace
2. Apps
3. Data
4. Research
5. Automations
6. Commerce
7. Security
8. Admin

Role-based visibility is defined in `src/keprix/ui_contract/navigation.py`.

## Web components

See `components/registry.json` for the canonical map from design-system names to `frontend/src/components/` paths.

## Cross-surface specs

- Mobile navigation: `../mobile/app-shell/navigation.json`
- TUI screens: `../tui/screens/navigation.json`
- Backend contract: `src/keprix/ui_contract/`

## App builder

Generated apps declare `app_ui` navigation and enabled modules but must use Keprix components and status language. Example:

```yaml
app_ui:
  app_name: Borehole Advisor
  navigation: [dashboard, records, jobs, reports, billing, settings]
  primary_record: borehole_project
  accent_role: field_services
  enabled_modules: [workspace, data, commerce, research]
```
