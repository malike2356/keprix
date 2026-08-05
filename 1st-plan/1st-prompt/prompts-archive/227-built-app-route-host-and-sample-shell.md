# Keprix - Prompt 227: Built App Route Host and Starter Sample

## Context

Host built app pages at `/apps/[slug]/*` using `BuiltAppLayout` and manifest from the registry (prompt **226**). Ship an in-repo **starter sample** so AbbiS and other consumers can copy the pattern.

Depends on **225**, **226**.

## Working directory

`/opt/lampp/htdocs/verlox/keprix/`

## Route structure

```text
frontend/src/app/(workspace)/apps/[slug]/layout.tsx
frontend/src/app/(workspace)/apps/[slug]/page.tsx              # dashboard / entry
frontend/src/app/(workspace)/apps/[slug]/[section]/page.tsx  # optional catch-all or explicit sections
```

Recommendation: use explicit routes for starter (`members`, `settings`); document catch-all pattern in docs for large apps.

### `layout.tsx`

- `useParams().slug`
- SWR `fetchBuiltAppManifest(slug)`
- Loading: `SkeletonList` or `AsyncView`
- Error: `Alert` + link back to Launcher
- Wrap children in `BuiltAppLayout` with fetched manifest
- Keep parent `(workspace)/layout.tsx` using `AppShell` (not chat shell)

### Workspace layout note

Update `frontend/src/app/(workspace)/layout.tsx` only if needed so `/apps/*` uses `AppShell` (should already). Do not nest a second platform sidebar.

## Starter sample

`examples/built-app-starter/`:

```text
built_app.yaml
README.md
```

Manifest id: `starter`. Sections: Dashboard (`/apps/starter`), Reports (`/apps/starter/reports`), Settings (`/apps/starter/settings`).

Pages: minimal MUI placeholders proving inner nav switches content.

Wire install script or document copy step:

```bash
mkdir -p "$KEPRIX_DATA_DIR/built_apps/starter"
cp examples/built-app-starter/built_app.yaml "$KEPRIX_DATA_DIR/built_apps/starter/"
```

## Hook

`frontend/src/hooks/useBuiltAppManifest.ts`:

- SWR key `built-app-manifest-{slug}`
- Returns `{ manifest, error, isLoading }`

## Tests

`frontend/src/app/(workspace)/apps/[slug]/layout.test.tsx` (mock manifest + router):

- Renders `BuiltAppLayout` with section labels
- Unknown slug shows error state

`tests/frontend/test_built_apps_navigation.py`:

- Route files exist
- `layout.tsx` imports `BuiltAppLayout`
- `examples/built-app-starter/built_app.yaml` exists

## Out of scope

- AbbiS production modules (consumer repo)
- SSR manifest loading optimization
- iframe embedding of external SPAs

## Acceptance criteria

- `/apps/starter` loads with inner section nav and 3 placeholder pages
- Platform sidebar still visible; only one "Starter app" entry in Installed apps
- Active section highlights correctly
- Tests pass

## Manual test

1. Install starter manifest
2. Click Installed apps > Starter app
3. Switch Reports / Settings via horizontal nav
4. Open Chat from platform sidebar; return to app; section state preserved via URL
