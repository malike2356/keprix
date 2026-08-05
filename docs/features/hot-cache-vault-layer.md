# Hot Cache Vault Layer

The hot cache is an optional `wiki/hot.md` rolling summary for workspace orientation.

Read order:

1. `wiki/hot.md` when present and enabled.
2. `wiki/index.md`.
3. Recent `wiki/log.md`.
4. Target wiki pages.

## API

- `GET /api/workspaces/{id}/hot-cache`
- `PUT /api/workspaces/{id}/hot-cache/config`
- `POST /api/workspaces/{id}/hot-cache/refresh`

Refresh is deterministic without an API key: callers can pass `summary` or `recent_text`, and Keprix caps the rendered hot cache to roughly 500 words.
