# Keprix - Prompt 226: Built Apps Registry and Launcher Nav Entries

## Context

Register installed **built apps** via manifest and expose **one sidebar entry per app** under group **Installed apps**. Inner module routes stay in `BuiltAppLayout` (prompt **225**), not in `NAV_ITEMS`.

Depends on **225** (manifest types), **223**.

## Working directory

`/opt/lampp/htdocs/verlox/keprix/`

## Backend

### 1. Module

Create `src/keprix/built_apps/`:

```text
__init__.py
manifest.py      # load + validate built_app.yaml
registry.py      # list installed apps from data dir
routes.py        # GET /api/built-apps, GET /api/built-apps/{id}
```

Install location (v1): `KEPRIX_DATA_DIR/built_apps/{id}/built_app.yaml` plus optional static assets path.

Seed on dev startup or via example copy: `examples/built-app-starter/built_app.yaml`.

### 2. API

| Method | Route | Auth | Response |
| --- | --- | --- | --- |
| GET | `/api/built-apps` | session | `{ apps: [{ id, label, description, entry, icon, version }] }` |
| GET | `/api/built-apps/{id}` | session | Full manifest including `navigation` block |

Do not expose filesystem paths in API responses.

### 3. UI contract

In `src/keprix/ui_contract/__init__.py`, add:

```python
"installed_apps": list_installed_apps_summary(),  # id, label, href, icon only
```

Add navigation group to `navigation.py`:

```python
NAV_GROUP_LABELS["installed_apps"] = "Installed apps"
# Insert in NAV_GROUPS_ORDER after "apps"
```

**Do not** add per-module items to `NAV_ITEMS`. Sidebar merges `installed_apps` from contract at render time (`navigationFromContract` in frontend).

### 4. Mount routes

Register `built_apps` router in `src/keprix/api/server.py`.

## Frontend

### 1. API client

`frontend/src/lib/built-apps-api.ts`:

- `fetchBuiltApps()`, `fetchBuiltAppManifest(id)`

### 2. Navigation merge

Update `frontend/src/lib/navigation.ts`:

- Extend `NavGroupId` with `installed_apps`
- `navigationFromContract`: append dynamic items from `contract.installed_apps` (or fetch SWR in Sidebar if contract too heavy; prefer contract field)

### 3. Sidebar

`Sidebar.tsx`: render `installed_apps` group using same `SidebarNavGroup` from **224**. Hide group when empty.

## Manifest schema

Validate required fields: `id`, `label`, `entry`. `navigation.items[].href` must start with `/apps/{id}`.

## Tests

`tests/built_apps/test_registry.py`:

- Load sample manifest from `examples/built-app-starter/`
- Reject manifest with href outside app prefix
- List endpoint returns summary without navigation blob

`tests/api/test_built_apps_routes.py`:

- GET list 200 when sample installed
- GET detail includes navigation
- 404 for unknown id

`tests/ui/test_ui_contract.py` (extend):

- `installed_apps` key present (array)

## Out of scope

- Zip install / marketplace for built apps
- Merging with `agent_apps` registry
- Role-based app visibility beyond admin-only flag (optional `roles: [admin]` in manifest v1)

## Acceptance criteria

- Sample app appears once in sidebar under Installed apps
- Full manifest available to layout via API
- UI contract includes `installed_apps`
- Pytest passes
- No AbbiS-specific routes in `navigation.py`

## Manual test

1. Copy starter manifest to data dir
2. Reload workspace; sidebar shows "Starter app" under Installed apps
3. `curl -H "Authorization: Bearer ..." /api/built-apps/starter` returns navigation block
