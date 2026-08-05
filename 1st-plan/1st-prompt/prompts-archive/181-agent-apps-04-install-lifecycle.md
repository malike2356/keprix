# Keprix Prompt 181: Agent Apps - Install, Update, and Uninstall Lifecycle

## Purpose

Frictionless **install without CLI**: upload zip bundle, validate, install; uninstall and
upgrade with version tracking. Registry v2 supports source metadata and installed path safety.

Read reference **177**. Requires prompt **178** (hub UI). Can parallel **179**/**180**.

---

## Dependencies

- `src/keprix/agent_apps/registry.py`
- `src/keprix/agent_apps/deployment_bundle.py`
- `src/keprix/agent_apps/routes.py`
- `POST /api/agent-apps/install` (path-based today)

---

## What to build

### 1. Registry v2

Extend `registry.py`:

```python
@dataclass
class InstalledApp:
    name: str
    version: str
    path: str
    installed_at: str
    source: str          # template | upload | path | studio | hub
    source_id: str | None
```

Persist in `~/.keprix/agent_apps/installed.json` (migrate v1 rows on read).

Methods:

- `install(source: Path, *, source: str, source_id: str | None) -> InstalledApp`
- `uninstall(name: str) -> None`  # remove dir under apps root + registry row
- `upgrade(name: str, new_source: Path) -> InstalledApp`  # backup old, atomic swap
- `get(name: str) -> InstalledApp | None`

Never install outside `KEPRIX_AGENT_APPS_DIR` (configurable, default `~/.keprix/agent_apps/apps/`).

### 2. Zip upload endpoint

```python
@router.post("/install/upload")
async def install_agent_app_upload(file: UploadFile, ...):
    """
    Accept .zip deployment bundle.
    Extract to temp dir -> validate manifest -> copy to apps dir -> register.
    """
```

Max size: 25 MB (config). Reject path traversal in zip entries.

Reuse `deployment_bundle.py` validation; ensure secrets stripped on export match install checks.

### 3. Uninstall and upgrade routes

```python
DELETE /api/agent-apps/{name}
POST /api/agent-apps/{name}/upgrade   # body: path or upload
GET /api/agent-apps/{name}/export     # download zip (existing bundle builder)
```

On uninstall: remove linked cron jobs if any (stub hook for **183**).

### 4. Frontend: install flow

```text
frontend/src/app/(workspace)/agent-apps/install/page.tsx
frontend/src/components/agent-apps/AgentAppInstallWizard.tsx
```

Steps:

1. **Choose source**: Upload zip | Local path (admin/dev only)
2. **Validate**: call `POST /validate` or upload preview endpoint
3. **Confirm**: show manifest summary (name, version, permissions, required_env)
4. **Install**: success -> redirect to `/agent-apps/{name}`

Drag-and-drop zip on hub empty state optional.

### 5. App detail actions

On `/agent-apps/[slug]`:

- **Export bundle** (download)
- **Uninstall** with confirmation dialog
- **Upgrade** when newer version detected (compare semver)

### 6. Security

- Path install restricted to `KEPRIX_DEV_MODE=true` or admin role
- Upload requires authenticated user
- Audit log entry: `agent_app.installed`, `agent_app.uninstalled` (if audit module exists)

---

## Acceptance criteria

- [ ] Upload hello-agent zip installs and appears in hub.
- [ ] Uninstall removes app and registry entry.
- [ ] Upgrade replaces version atomically.
- [ ] Path traversal in zip rejected.
- [ ] Tests: `tests/agent_apps/test_registry_v2.py`, `test_install_upload.py`.

---

## Out of scope

- Marketplace catalog install (**182**)
- Billing install limits (**184**)

---

## Archive

On completion: move to `prompts-archive/`.
