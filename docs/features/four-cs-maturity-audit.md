# Four C's Maturity Audit

The Four C's audit scores Agent OS readiness across:

- Context
- Connections
- Capabilities
- Cadence

Scores are deterministic and file-backed. Missing files produce low scores with concrete gaps.

## API

- `POST /api/agent-os/maturity/run`
- `GET /api/agent-os/maturity`
- `GET /api/agent-os/maturity/{audit_id}`
- `POST /api/agent-os/maturity/{audit_id}/export-to-level-up`

## CLI

```bash
keprix agent-os maturity run --workspace-id personal-os
keprix agent-os maturity list
keprix agent-os maturity show mat-...
keprix agent-os maturity export mat-... --to-level-up
```

The export payload uses schema `keprix.level_up.input.v1`.
