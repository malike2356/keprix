# Scout connector

Labyrinth Scout is an optional governance and audit console.

## Enable

```bash
KEPRIX_GOVERNANCE_ENABLED=true
KEPRIX_GOVERNANCE_API_KEY=
KEPRIX_GOVERNANCE_WORKSPACE_ID=
KEPRIX_GOVERNANCE_ENDPOINT=https://api.labyrinthscout.com
```

## UI

Settings: `/settings/governance`

## Events

Audit and clinical events queue locally then flush to Scout. See [Audit log](../security/audit-log.md).
