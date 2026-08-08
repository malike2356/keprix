# Keprix - Prompt 279: Google Workspace connector

**Series:** Nate Herk AIOS adoption **274-279**  
**Master reference:** `../prompts-archive/ref-273-nate-herk-aios-adoption-master-reference.md`  
**Depends on:** **277**  
**Working directory:** `/opt/lampp/htdocs/verlox/keprix/`

---

## 1. What this prompt builds

**Google Workspace connector** (GWS-style): one integration surface for Gmail, Calendar, Drive, Docs, and Sheets via OAuth desktop flow + CLI/sidecar bridge (Nate GWS CLI pattern). Registers in **277** tier-1 domains (`calendar`, `comms`, `knowledge`) and **234** connector catalog.

Agent tools (names stable in Keprix):

| Tool | Purpose |
| --- | --- |
| `gws_gmail_list` | List/search messages |
| `gws_gmail_send` | Send draft (confirm gate) |
| `gws_calendar_list` | Upcoming events |
| `gws_calendar_create` | Create event (confirm gate) |
| `gws_drive_search` | Find files |
| `gws_sheets_read` | Read range |

**Non-goals:**

- Shipping Google's `gws` binary inside Keprix core (sidecar or `uv` optional dep)
- Full Admin SDK / Workspace user provisioning
- Replacing all individual Google MCP servers (this is the curated Keprix connector)

---

## 2. Architecture

```text
Settings: GOOGLE_WORKSPACE_CREDENTIALS_PATH
        |
        v
google_workspace_bridge.py
  - OAuth token store (encrypted local)
  - spawn gws CLI OR google-api-python-client fallback
        |
        v
gws_* tools in toolsets.py (comms profile)
        |
        v
connections.md mark calendar/comms/knowledge live
```

---

## 3. Configuration

```yaml
google_workspace:
  enabled: false
  credentials_path: ""       # OAuth client JSON (desktop app)
  token_path: ""             # auto: ~/.keprix/google-workspace-token.json
  scopes:
    - gmail.readonly
    - gmail.send
    - calendar
    - drive.readonly
    - spreadsheets.readonly
  service_account_mode: false  # prefer dedicated user per 277 docs
```

Env: `GOOGLE_WORKSPACE_CREDENTIALS_PATH`, `KEPRIX_GWS_ENABLED`

---

## 4. OAuth flow

CLI:

```bash
keprix integrations google-workspace login
keprix integrations google-workspace status
keprix integrations google-workspace logout
```

Web: `/settings/integrations/google-workspace` with connect button (opens OAuth URL).

Store tokens outside repo; document in `SECRETS_CHECKLIST` for **263** client kits.

---

## 5. Bridge implementation

**Preferred:** optional `scripts/gws_bridge.py` wrapping official Google APIs (no undocumented Google CLI dependency required for v1).

**Optional:** if `gws` CLI on PATH, delegate via subprocess (feature flag `use_gws_cli`).

Unified error messages for missing APIs enabled in Google Cloud Console (Nate demo parity).

---

## 6. Connector catalog entry (**234** hook)

```json
{
  "id": "google-workspace",
  "name": "Google Workspace",
  "tier1_domains": ["calendar", "comms", "knowledge"],
  "tools": ["gws_gmail_list", "gws_calendar_list", "gws_drive_search"],
  "setup_url": "/settings/integrations/google-workspace"
}
```

---

## 7. API routes

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/integrations/google-workspace/status` | connected / scopes |
| POST | `/api/integrations/google-workspace/oauth/start` | Auth URL |
| POST | `/api/integrations/google-workspace/oauth/callback` | Exchange code |
| DELETE | `/api/integrations/google-workspace` | Revoke |

---

## 8. Files to create

```
src/keprix/integrations/google_workspace/
  __init__.py
  bridge.py
  oauth_store.py
  tools_gmail.py
  tools_calendar.py
  tools_drive.py
  tools_sheets.py

src/keprix/tools/
  gws_gmail_list.py
  gws_calendar_list.py
  ... (or register from integration module)

src/keprix/api/
  google_workspace_routes.py

src/keprix/keprix_cli/
  google_workspace_commands.py

frontend/src/app/(workspace)/settings/integrations/google-workspace/page.tsx

docs/integrations/google-workspace.md

tests/integrations/google_workspace/
  test_bridge_mock.py
  test_oauth_store.py
  test_gws_tools.py
```

Register tools in `toolsets.py` under comms/productivity profiles.

---

## 9. Acceptance criteria

- OAuth login flow stores token; status returns `connected: true` (mock in tests).
- `gws_calendar_list` returns structured JSON from API mock.
- Send/create tools require `confirm: true` parameter or user approval gate.
- **277** wizard marks `calendar` live when connector connected.
- Missing credentials returns actionable setup error (no stack trace to user).
- `.env.example` documents vars; no secrets committed.
- Connector appears in catalog stub for **234**.

---

## 10. Dependencies

- **Requires:** **277** connections matrix
- **Soft:** **234** marketplace UI
- **Related:** **263** client kit secrets checklist
