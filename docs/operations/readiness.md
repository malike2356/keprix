# Readiness

Market, upgrade, and recovery gates for a Keprix instance. The CLI and Admin UI share the same report service.

Statuses: `pass`, `warn`, `fail`, `unknown`. Failed checks include a `fix_path` for admin navigation.

## CLI

```bash
keprix readiness
keprix readiness --json
keprix readiness --category market
keprix readiness --category upgrade --target 0.16.0
keprix readiness --category recovery
```

`--target` checks package installability for an upgrade version (`keprix==VERSION`). Categories: `market`, `upgrade`, `recovery`, `all` (default).

Equivalent module entrypoint:

```bash
PYTHONPATH=src python3 -m keprix.keprix_cli.main readiness
```

## Admin UI

Open **Admin > Readiness** at `/admin/readiness` (admin or owner). The UI calls `GET /api/admin/readiness` and can trigger a safe backup from the same surface.

See [Admin dashboard](admin-dashboard.md).

## What is checked

Representative gates (exact list grows with the readiness module):

| Area | Examples |
| --- | --- |
| Market | Auth, billing price pins, BYOK/wallet, quotas, tool ACLs, client approval, public docs, triggers |
| Upgrade | Package installability, backup path, version migration hooks |
| Recovery | Backup creation/encryption/retention, restore-test evidence |

## Billing and Community Edition

Billing is optional for self-hosted Community Edition.

- When billing config is absent, the billing-prices check is `warn` (hosted SaaS may still require pins).
- Paid plan/addon Stripe price IDs must be present when billing config is loaded; missing required pins fail market readiness.
- Community Edition coffee donation is voluntary. Missing donation price IDs are warn-only and **never** block readiness.

Details: [Billing](../features/billing.md).

## Private ship gate

CI / pre-ship automation should use:

```bash
bash scripts/check-private-ship-gate.sh
```

That script is the private ship gate (architecture, auth/billing focus, TUI parity, frontend typecheck, and related smoke). It may be added or updated by a sibling prompt; when present, run it before declaring a private cut ready.

## Public GTM gate

Before calling Keprix **public GTM ready**, run:

```bash
bash scripts/check-public-gtm-gate.sh
```

This gate fail-closes until anonymous GitHub is reachable, forbids workspace abs paths and historical wrong-domain marketing placeholders on the ship face, checks installer syntax and PyPI honesty, reuses the private ship gate, and verifies marketing install snippets. Soft skips:

| Env | Effect |
| --- | --- |
| `KEPRIX_SKIP_DOMAIN_CHECK=1` | Skip `https://keprixai.com/` only while Contabo origin is intentionally deferred |
| `KEPRIX_PUBLIC_GTM_SKIP_PRIVATE=1` | Surface-only preview (CI); do not use for sign-off |
| `KEPRIX_PYPI_PUBLISHED=1` | After owner PyPI upload (honesty script) |

CI runs a surface preview; after publicize, keep the job hard-failing on regressions (drop `continue-on-error` when green). Release / public sign-off should run the full gate (no `KEPRIX_PUBLIC_GTM_SKIP_PRIVATE`) when claiming READY. Sign-off: [Public GTM sign-off](../architecture/public-gtm-signoff.md).

Package version for the current private ship target is **0.16.0** (`pyproject.toml`). See [Changelog](../reference/changelog.md).

## Related

- [keprixai.com Contabo origin](keprixai-com-origin.md)
- [Public GitHub checklist](public-github-checklist.md)
- [VPS deploy](vps-deploy.md)
- [Hardening](../security/hardening.md)
- [Backup](backup.md)
- [CLI reference](../reference/cli.md)
