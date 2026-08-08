# Keprix - Prompt 263: Client Kit and Simplified Mode

**Series:** Agentic OS adoption **256-265** (Level 4 distribution)  
**Master reference:** `../prompts-archive/ref-255-agentic-os-adoption-master-reference.md`  
**Depends on:** **262**  
**Working directory:** `/opt/lampp/htdocs/verlox/keprix/`

---

## 1. What this prompt builds

**Client Kit** export: zip bundle for handoff to non-technical users (team/client) containing action board pins, promoted automations, workspace template, vault path readme, secrets checklist. **Simplified mode** hides advanced routes (YAML editor, terminal, mutation, raw playbook JSON) for kit recipients.

Chase insight: raise the floor; buttons not terminal.

**Non-goals:** Multi-tenant hosting; Obsidian-based distribution path (document manual vault copy only).

---

## 2. Kit contents

```text
client-kit-{name}-{date}.zip
  manifest.json           # kit version, keprix min version
  action-board.json       # from 262
  automations/
    cron/                 # exported job specs
    playbooks/*.yaml
    agent-apps/*/agent.yaml
  workspace-template/       # optional 258 snapshot (no secrets)
  KEPRIX.md
  SECRETS_CHECKLIST.md    # required env vars, vault keys
  SETUP.md                # import steps
```

---

## 3. Export / import API

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/api/agent-os/client-kit/export` | Build zip |
| POST | `/api/agent-os/client-kit/import` | Upload zip (admin) |
| GET | `/api/agent-os/client-kit/preview` | What will export |

CLI:

```bash
keprix agent-os client-kit export --name acme --output ./acme-kit.zip
keprix agent-os client-kit import ./acme-kit.zip
```

---

## 4. Simplified mode

Config:

```yaml
display:
  simplified_mode: false   # or per-user flag
```

When enabled, hide sidebar routes:

- Playbooks advanced YAML / JSON
- Agent Studio MCP workbench
- Mutation engine
- Terminal / coding workspace (optional sub-flag)
- Admin control center (always admin-gated)

Show prominently:

- `/agent-os` action board
- `/agent-apps` installed apps
- Chat (optional)
- Documents (read-only optional)

Settings UI: **Admin > Client experience > Simplified mode** (default off). Per-user override for kit recipients.

---

## 5. UI

`/settings/agent-os/client-kit`

- Select pins/automations to include
- Include workspace template toggle
- Export button
- Import wizard for admins

Post-import: prompt to complete secrets checklist and enable simplified mode for selected users.

---

## 6. Files to create

```
src/keprix/agent_os/
  client_kit_exporter.py
  client_kit_importer.py
  simplified_mode.py        # route guard + feature flags

src/keprix/api/agent_os_client_kit_routes.py

frontend/src/app/(workspace)/settings/agent-os/client-kit/page.tsx
frontend/src/lib/simplifiedMode.ts

docs/features/agent-os-client-kit.md

tests/agent_os/
  test_client_kit_export_import.py
  test_simplified_mode.py
```

---

## 7. Acceptance criteria

- Export produces valid zip; import on fresh temp `KEPRIX_HOME` restores pins and cron jobs.
- Simplified mode hides configured routes in sidebar and blocks direct URL access with friendly redirect to `/agent-os`.
- SECRETS_CHECKLIST lists only keys referenced by bundled automations (no values).
- Import requires admin role.
- Roundtrip test: export -> import -> headless pin run succeeds with secrets mocked.

---

## 8. Dependencies

- **265** onboarding marks "Distribute kit" step complete after export
