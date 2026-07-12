# Agent OS Phase 5 polish

Ship-ready defaults for token cost control, VPS/managed deploy, guardrails, and the error paste loop.

## Token minimization playbook (Task 5.1)

Ten techniques mapped to existing Keprix code:

```bash
keprix agent-os playbook
keprix agent-os playbook --markdown
```

API: `GET /api/agent-os/token-playbook`

UI: Ship defaults panel on `/agent-os/glass` (playbook, guardrails + backup, error-paste).

## Server deploy (Task 5.2)

**Primary:** Compose + Caddy via production script:

```bash
bash scripts/generate-production-env.sh --domain https://app.example.com
bash scripts/deploy-keprix-production.sh --bootstrap --domain app.example.com --skip-scout
```

Helpers: `deploy-server.sh` (low-level), `deploy-canary.sh`, `bootstrap-do-droplet.sh`.

See [VPS deploy](../operations/vps-deploy.md).

## Managed hosting (Task 5.3)

Optional helpers only (not one-click):

```bash
bash scripts/bootstrap-do-droplet.sh --domain app.example.com --email you@example.com --ssh-key NAME --ref v0.16.0
bash scripts/deploy-managed.sh fly   # requires Postgres/Redis/volume; see fly.fullstack.toml
```

Fly fullstack: `fly.fullstack.toml` + `docker/Dockerfile.fly`. Backend-only sketch: `fly.backend-only.toml`.

## Guardrails defaults (Task 5.4)

Restricted workspace under `~/.keprix/workspace`, approvals default to manual, vault auto-backup before writes.

```bash
keprix agent-os guardrails
keprix agent-os guardrails backup-vault
```

Env knobs:

| Variable | Default | Meaning |
| --- | --- | --- |
| `KEPRIX_GUARDRAILS_DEFAULT` | `true` | Enable default guardrails |
| `KEPRIX_VAULT_AUTO_BACKUP` | `true` | Snapshot vault before writes |
| `KEPRIX_VAULT_BACKUP_MIN_INTERVAL_SEC` | `300` | Throttle between snapshots |
| `KEPRIX_WORKSPACE_ROOT` | `~/.keprix/workspace` | Allowed agent workspace |
| `KEPRIX_APPROVALS_MODE` | `manual` | Require approval for destructive work |

API: `GET /api/agent-os/guardrails`, `POST /api/agent-os/guardrails/backup-vault`

Vault PUT routes and optional capture (`KEPRIX_VAULT_BACKUP_EVERY_CAPTURE=true`) call the backup helper.

## Error paste loop (Task 5.5)

Paste a traceback; Keprix classifies it and returns a minimal fix plan, then asks for the next paste after you re-run.

```bash
keprix agent-os workflow error-paste --error "ModuleNotFoundError: No module named foo"
```

Catalog app: `error-paste`. API: `POST /api/agent-os/error-paste`.

## Related

- [Agent OS overview](agent-os-overview.md)
- [Phase 4 workflows](agent-os-phase4-workflows.md)
