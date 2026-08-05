# Google Workspace connector

The Google Workspace connector exposes Gmail, Calendar, Drive, Docs, and Sheets through one Keprix integration. It is designed for a desktop OAuth client and an optional local sidecar bridge.

## Configuration

Set these environment variables outside the repository:

```bash
export KEPRIX_GWS_ENABLED=1
export GOOGLE_WORKSPACE_CREDENTIALS_PATH=/secure/path/oauth-client.json
export GOOGLE_WORKSPACE_TOKEN_PATH=~/.keprix/google-workspace-token.json
export GOOGLE_WORKSPACE_BRIDGE_CMD="/path/to/gws-bridge"
```

Enable the Gmail, Calendar, Drive, and Sheets APIs in Google Cloud. The OAuth client should be a desktop app. Tokens are written to `GOOGLE_WORKSPACE_TOKEN_PATH`, defaulting to `~/.keprix/google-workspace-token.json`.

## CLI

```bash
keprix integrations google-workspace status
keprix integrations google-workspace login
keprix integrations google-workspace callback --code "$CODE"
keprix integrations google-workspace logout
```

The web settings page is `/settings/integrations/google-workspace`.

## Tools

Stable tool names:

| Tool | Purpose |
| --- | --- |
| `gws_gmail_list` | List or search messages |
| `gws_gmail_send` | Send a message, requires `confirm: true` |
| `gws_calendar_list` | List upcoming events |
| `gws_calendar_create` | Create an event, requires `confirm: true` |
| `gws_drive_search` | Search Drive files |
| `gws_sheets_read` | Read a Sheet range |

When OAuth callback succeeds, Keprix marks the `calendar`, `comms`, and `knowledge` domains live in `connections.md` when that workspace matrix exists.
