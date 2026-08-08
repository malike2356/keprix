# Built apps navigation build order

Reference for prompts **223-228**. Architecture reference:
`prompts-archive/ref-223-built-apps-navigation-architecture-reference.md`.

## Sequence

```text
223 Architecture reference (planning only)
224 Collapsible platform sidebar groups
225 BuiltAppLayout component kit
226 Built apps registry + UI contract + sidebar entries
227 /apps/[slug] route host + starter sample
228 Docs, tests, archive series
```

## Prompt summary

| # | Title | Delivers |
| --- | --- | --- |
| 223 | Architecture reference | This doc + build order (not archived) |
| 224 | Collapsible sidebar | `Sidebar.tsx` group collapse, persistence, a11y, tests |
| 225 | BuiltAppLayout kit | `components/built-app/*`, types, Storybook-free dev page optional |
| 226 | Registry + nav API | `built_apps/` module, `GET /api/built-apps`, UI contract `installed_apps` |
| 227 | Route host + sample | `/apps/[slug]/*`, `examples/built-app-starter`, pytest + vitest guards |
| 228 | Docs + verification | `docs/features/built-apps-navigation.md`, index link, archive 224-228 |

## Dependencies

| Prompt | Requires |
| --- | --- |
| 224 | **136** workspace shell, **22** UI foundation |
| 225 | **116** theme tokens (recommended), MUI patterns in `AppShell` |
| 226 | 225 types (manifest shape), `ui_contract` |
| 227 | 225, 226 |
| 228 | 224-227 |

## Parallel work

- **224** and **225** can start together after **223**.
- **226** needs manifest types from **225** (share `built-app-manifest.ts` in frontend + Python schema in 226).
- AbbiS eng UI in `apps-on-keprix/abbis/` is a **consumer**; not part of 224-228 AC.
