# Private ship sign-off

Date: 2026-07-27

Scope: private / invite OSS soft ship of Keprix Community Edition.
Not a public GTM or paid-at-scale launch.

## Gate evidence

Run from `/opt/lampp/htdocs/verlox/keprix` with the project venv (Python 3.11+):

| Check | Result |
| --- | --- |
| `bash scripts/check-private-ship-gate.sh` | Pass (architecture, auth, billing, TUI parity, TUI surpass, agent parity, frontend tsc) |
| `bash scripts/check-tui-parity.sh` | Pass (100/100) |
| `bash scripts/check-tui-surpass-hermes.sh` | Pass |
| `bash scripts/check-agent-parity.sh` | Pass (10/10) |
| `cd frontend && npx tsc --noEmit` | Pass (exit 0) |
| `.venv/bin/python -m pytest tests/api -q` | Pass (86 passed, 2 skipped) |
| `.venv/bin/python -m pytest tests/architecture tests/auth tests/billing -q` | Pass |

## Hermes comparison and surpass

- Behavior parity: Keprix TUI matches Hermes interaction contracts without copying Ink visuals.
- Surpass: Command Center, runtime timeline, tool cards, and proof harnesses are Keprix-better.
- Agent runtime: local agent parity gate 10/10; deliberate differences remain (Textual vs Ink, Channel Shield gateway ownership, branding).

## Deploy path

Primary private deploy:

```bash
bash scripts/generate-production-env.sh --domain https://app.example.com
bash scripts/deploy-keprix-production.sh --bootstrap --domain app.example.com --skip-scout
```

Docs: `docs/operations/vps-deploy.md`, `docs/operations/readiness.md`,
`docs/getting-started/cloud-deploy.md`.

## Community Edition rules

- Billing defaults off (`KEPRIX_BILLING_ENABLED=false`).
- Coffee donation is optional and must never gate CE use.
- Stripe price IDs are operator-owned; do not invent new catalog prices from code.

## Baggage quarantine

- `1st-plan/competitor-research/` moved under `/opt/lampp/htdocs/verlox/archive/keprix-wip-bakups/` and gitignored.
- `apps-on-keprix/retired-project-compasslab/` moved to the same archive root and gitignored.

## Remaining risks (honest)

1. Working tree may still be dirty relative to `origin/main`. Tag from a curated clean commit, not an accidental `tar` of the WIP cwd.
2. Hosted SaaS legal text and company entity fields are still incomplete for public paid launch.
3. Public domain `keprixai.uk` was not verified live in this pass.
4. Full-suite beyond the private gate (every optional integration) was not claimed green.
5. Do not publish `.env`, `config/billing.yaml`, or Stripe credential files.

## Verdict

Ready for **private OSS soft ship / invite preview** after cutting a clean tag from a curated tree and following the VPS deploy docs.

Not ready for broad public GTM or mandatory paid conversion.
