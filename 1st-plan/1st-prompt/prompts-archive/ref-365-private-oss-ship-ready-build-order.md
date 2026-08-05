# Ref 365: Private OSS ship-ready build order

## Goal

Make Keprix safe to soft-ship privately as useful open source: strip baggage,
close quality blockers, re-prove Hermes parity/surpass, and document deploy.

This is **not** public GTM. Target: clean private tag / invite preview.

## Execution order

| Prompt | Title | Depends on |
| --- | --- | --- |
| 365 | Quarantine baggage and harden .gitignore | none |
| 366 | Restore wiped frontend modules and typecheck green | 365 |
| 367 | Hermes parity + surpass re-proof and comparison closeout | 366 |
| 368 | API auth fixtures and release CI gate | 366 |
| 369 | Ops docs, env docs, version/changelog sync | 365 |
| 370 | Deploy readiness script and private ship sign-off | 367, 368, 369 |

## Non-goals

- Creating new Stripe prices
- Public marketing domain launch
- Full SaaS legal entity fill (note remaining legal gaps in sign-off)
- Deleting production data or secrets

## Definition of done

1. Competitor clone and retired Compasslab leftovers are outside the ship tree or gitignored.
2. `cd frontend && npx tsc --noEmit` exits 0.
3. `bash scripts/check-tui-parity.sh` and `bash scripts/check-tui-surpass-hermes.sh` pass.
4. `bash scripts/check-agent-parity.sh` passes (10/10).
5. Focused release gate script passes (auth/API smoke + architecture + pipx smoke).
6. `docs/operations/vps-deploy.md` and `docs/operations/readiness.md` are non-empty and accurate.
7. Package version and CHANGELOG story are consistent enough for a private tag note.
8. Ship sign-off doc lists remaining known risks honestly.
