# Keprix Prompt 366: Restore wiped frontend modules and typecheck green

## Purpose

Close frontend ship blockers: empty/wiped modules that break HMR and `tsc`,
plus remaining type errors on the private-ship path.

## Tasks

1. Restore from `git HEAD` any tracked file wiped in the worktree that still has
   content on HEAD (Agent OS subnav/layout/glass/galaxy/ShipDefaults, etc.).
2. Implement previously empty-but-required modules so they are real modules:
   - `frontend/src/lib/a2a-api.ts` (wire to `/api/a2a/*`)
   - `frontend/src/lib/observability-api.ts` (wire to `/api/observability/*`)
   - `InstallButton`, `UpgradeWizardDialog`, `PlaybookStudioShell`,
     `StudioHandoffGate`, `BillingWalletCard`, `SuggestConnectorChip`,
     `ClientApprovalPanel`, `ResourceAclPanel`, `calendar-motion`
   - Empty admin/settings page stubs that are routed must render a safe page
     (header + short copy + link back), not a blank module.
3. Add missing `normalizePublicApiBase` export used by `ce-api.test.ts`, or
   update the test to match the real API helper if the helper moved.
4. Fix remaining `tsc` errors in auth SSO callback, usage charts, research
   shell, marketing deferred sections, AgentAppRunForm, analytics page.
5. Prefer restoring existing patterns from sibling components and backend
   route docs over inventing new product surface.

## Verification

```bash
cd frontend && npx tsc --noEmit
find frontend/src -type f \( -name '*.ts' -o -name '*.tsx' \) \( -empty -o -size 1c \) | wc -l
# expect 0 for ship-critical paths under lib/components/app
```
