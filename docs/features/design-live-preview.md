# Design Live Preview

Design Live Preview opens local HTML artifacts in a sandboxed iframe at `/design/preview`.

## Capabilities

- Open an `index.html` file or a project directory under the configured workspace root.
- Click a rendered DOM node to capture selector, HTML snippet, tag, classes, and bounding box metadata.
- Copy selector/snippet or build an agent message for `claude-design` plus the optional `impeccable` skill.
- Watch the entry file and reload the iframe when it changes.

## API

- `POST /api/design/preview/open`
- `GET /api/design/preview/{session_id}`
- `POST /api/design/preview/{session_id}/selection`
- `GET /api/design/preview/{session_id}/url`
- `GET /api/design/preview/{session_id}/render`
- `GET /api/design/preview/{session_id}/events`

Preview sessions are persisted under `{KEPRIX_HOME}/design/preview/{session_id}.json`.

## Security

Local paths must resolve under the server working directory, a registered Builder project path, or `KEPRIX_WORKSPACE_ROOT`. Traversal outside those roots is rejected.

Remote URL preview is intentionally not supported.

## Configuration

```yaml
design:
  preview:
    enabled: true
```

Environment:

- `KEPRIX_DESIGN_PREVIEW_ENABLED=true`
- `KEPRIX_WORKSPACE_ROOT=/path/to/workspace`
