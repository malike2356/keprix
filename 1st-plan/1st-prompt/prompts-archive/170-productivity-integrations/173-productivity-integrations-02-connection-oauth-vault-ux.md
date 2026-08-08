# Keprix Prompt 173: Productivity Integrations - Connection, OAuth, and Vault UX

## Purpose

Make Notion and Trello **usable end-to-end** from `/admin/mcp` without CLI expertise: OAuth
connect for Notion, credential setup for Trello, connection status on server cards, and
optional Vault-backed secrets.

Read `prompts-archive/ref-171-productivity-notion-trello-architecture-reference.md`. Requires prompt **172**.

---

## Dependencies

- Prompt 172 complete (catalog entries + `auth_type: oauth` on add).
- `src/keprix/tools/mcp_oauth.py`, `mcp_oauth_manager.py` (existing OAuth for Linear/Notion tests).
- `src/keprix/keprix_cli/mcp_config.py`: `_oauth_tokens_present()`, `cmd_mcp_login`.
- Vault: read how other admin flows resolve secrets (`src/keprix/vault/` or credential helpers).

---

## What to build

### 1. Backend: connection status on server summary

In `mcp_admin_routes.py` `_mcp_server_summary()` (or equivalent), add:

```python
oauth_connected: bool  # True when auth==oauth and tokens present
connection_status: str  # "connected" | "needs_oauth" | "needs_credentials" | "disabled" | "error"
connection_error: Optional[str]  # last probe/connect error if any
```

Logic:

| Condition | `connection_status` |
| --- | --- |
| `enabled: false` | `disabled` |
| `auth: oauth` and tokens missing | `needs_oauth` |
| `auth: oauth` and tokens present | `connected` (or `error` if last test failed) |
| stdio with missing required env (check catalog or config) | `needs_credentials` |
| stdio/http with tools listed on last successful test | `connected` |

Reuse `_oauth_tokens_present(name)` from `mcp_config.py`. Do not expose token values.

### 2. Backend: OAuth start endpoint

Add to `mcp_admin_routes.py`:

```python
@router.post("/api/mcp/servers/{name}/oauth/start")
async def start_mcp_oauth(name: str, profile: Optional[str] = None):
    """
    Begin OAuth for an MCP server with auth: oauth.
    Returns { authorization_url: str } for the frontend to open in a new tab,
    or { ok: true, message: "Already connected" } when tokens exist.
    """
```

Implementation notes:

- Read server config; 404 if missing; 400 if `auth != oauth`.
- Delegate to `mcp_oauth_manager.get_manager()` same as `cmd_mcp_login`.
- If browser open is only possible server-side, document fallback: return URL only.
- Add `POST /api/mcp/servers/{name}/oauth/complete` only if the OAuth manager requires a
  callback hook; otherwise polling `GET /api/mcp/servers` after user completes browser flow is enough.

### 3. Backend: Vault resolve on catalog add

Extend `MCPCatalogAddBody`:

```python
vault_env: Dict[str, str] = {}  # env_var_name -> vault_secret_id
```

When `vault_env` is provided:

- Resolve each secret from Vault store (read existing vault API pattern).
- Merge resolved values into `env` before `_save_mcp_server`.
- Never return resolved values on subsequent GET (redaction unchanged).

Add `GET /api/mcp/vault/secret-keys` (admin only) returning `{ keys: string[] }` for picker UI,
or reuse an existing vault list endpoint if one exists (prefer reuse).

### 4. Frontend: server card connection UX

**`frontend/src/lib/admin-api.ts`**

- Extend `McpServer` with `oauth_connected?`, `connection_status?`, `connection_error?`.
- Add `startMcpOAuth(name: string): Promise<{ authorization_url?: string; ok?: boolean }>`.
- Extend `addMcpFromCatalog` opts with `vault_env?: Record<string, string>`.

**`frontend/src/app/(workspace)/admin/mcp/page.tsx`**

On each server card:

| `connection_status` | UI |
| --- | --- |
| `needs_oauth` | Warning chip + **Connect** button calls `startMcpOAuth`, opens URL in new tab |
| `needs_credentials` | Warning chip + **Edit** opens dialog to add env |
| `connected` | Success chip |
| `error` | Error chip + tooltip with `connection_error` |
| `disabled` | Default chip (existing) |

After OAuth URL opened, poll `mutateServers()` every 3s for 60s or until `oauth_connected`.

Catalog credential dialog additions:

- Per env field: optional **From Vault** dropdown (lists vault keys).
- When vault selected, send `vault_env` instead of plaintext value.

### 5. Frontend: post-add flows

When adding **`notion`** from catalog:

- Success message: "Server added. Click Connect to sign in with Notion."
- Auto-switch to My servers tab; highlight the new row.

When adding **`trello`**:

- Success message includes link to `homepage` setup guide.

### 6. CLI parity

Ensure `keprix mcp login notion` still works after UI changes. Add tip in `keprix_cli/tips.py`:

```text
After adding Notion from /admin/mcp, click Connect or run `keprix mcp login notion`.
```

### 7. Tests

**API tests** (`test_dashboard_admin_endpoints.py` or new `test_mcp_oauth_admin.py`):

- Server with `auth: oauth`, no tokens: `connection_status == needs_oauth`.
- Mock OAuth manager: `POST .../oauth/start` returns `authorization_url`.
- Catalog add with mocked vault resolve writes env to config (vault mock).

**Frontend**: manual AC only unless project has MCP page component tests; document in agent brief.

---

## Acceptance criteria

1. Add Notion from catalog; card shows **Needs OAuth**; Connect opens authorization URL.
2. After mocked OAuth token storage, card shows **Connected**.
3. Add Trello with API key + token; card shows **Connected** after successful List tools.
4. Vault picker can supply `TRELLO_TOKEN` without displaying it in the add dialog response.
5. `GET /api/mcp/servers` never returns raw secrets or OAuth refresh tokens.
6. `keprix mcp login notion` still authenticates when UI is unused.
7. All new backend tests pass.

---

## What this prompt does NOT do

- Notion RAG connector (prompt 174).
- Trello skill (prompt 175).
- Full operator guide (prompt 176).
