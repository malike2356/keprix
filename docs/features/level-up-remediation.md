# Level-up Remediation

Level-up consumes the Four C's maturity audit export and turns gaps into ordered remediation actions.

## API

- `POST /api/agent-os/level-up/generate`
- `GET /api/agent-os/level-up/{plan_id}`
- `POST /api/agent-os/level-up/{plan_id}/actions/{action_id}/complete`
- `POST /api/agent-os/level-up/{plan_id}/apply-safe-stubs`
- `POST /api/agent-os/level-up/{plan_id}/re-audit`

Safe auto-fixes are limited to empty context templates and `connections.md` stubs inside the selected workspace.
