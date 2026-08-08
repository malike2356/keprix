# Prompt: Adopt Readiness And Recovery Gates For Keprix

## Goal

Make Keprix market-readiness, upgrade-readiness, and recovery-readiness visible and enforceable.

## Source Research

Reference only:

- `/opt/lampp/htdocs/verlox/keprix/1st-plan/competitor-research/00-agents-to-adopt/myapi-open/docs/PRODUCTION_READINESS_CHECKLIST.md`
- `/opt/lampp/htdocs/verlox/keprix/1st-plan/competitor-research/00-agents-to-adopt/myapi-open/docs/SECURITY_AUDIT_OPERATIONS.md`
- `/opt/lampp/htdocs/verlox/keprix/1st-plan/competitor-research/00-agents-to-adopt/myapi-open/src/lib/backup-manager.js`
- `/opt/lampp/htdocs/verlox/keprix/1st-plan/competitor-research/00-agents-to-adopt/myapi-open/docs/DATA_RECOVERY_GUIDE.md`

Do not copy AGPL code. Reimplement the checklist and controls in Keprix style.

## Required Behavior

- Add readiness checks for auth, billing, BYOK, managed wallet, quotas, tool ACLs, backups, restore test evidence, upgrade path, self-knowledge RAG, version migration, and public docs.
- Add upgrade-readiness checks so the upgrade flow does not hang at backup or try unavailable package versions.
- Add recovery checks that verify backup creation, backup encryption, retention, and restore evidence.
- Add market-readiness status with pass, warn, fail, and unknown.
- Add admin/developer UI and CLI access to the same checks.
- Link each failed check to a fix path.
- Keep Community Edition donation voluntary and separate from readiness.

## Implementation Targets To Inspect

- `docs/features/migration.md`
- `docs/features/billing.md`
- `docs/features/control-center.md`
- `docs/features/agent-os-overview.md`
- `docs/operations`
- `src`
- `web`
- Upgrade flow, backup flow, onboarding, version display, and self-knowledge RAG modules.

## Implementation Steps

1. Inventory current readiness, onboarding, upgrade, backup, and migration checks.
2. Create one canonical readiness service with typed check results.
3. Add checks for package availability before install.
4. Add backup timeout, progress, failure reason, and recovery messaging.
5. Add restore-evidence tracking.
6. Add UI cards for launch readiness, upgrade readiness, and recovery readiness.
7. Add CLI command for the same report.
8. Add docs that explain how to clear each fail-level item.

## Tests

- Upgrade readiness fails when target package is unavailable.
- Backup failure reports a reason instead of hanging.
- Readiness fails when billing points at missing Stripe price IDs.
- Recovery readiness warns when restore evidence is missing.
- CLI and UI return consistent check results.

## Done Criteria

- Keprix can answer whether it is market ready with evidence.
- Upgrade flow failure modes are explicit.
- Backup and restore status is trustworthy.
- Readiness checks are visible in both UI and CLI.
- No AGPL code is copied.
