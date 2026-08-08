# Keprix Desktop Native Migration

**Status: IN PROGRESS**

## Current answer

The TUI presents Keprix branding to users. Its remaining Hermes references are internal parity notes and source comments, not product identity.

The desktop is branded as Keprix, but it is not yet fully independent from the inherited Hermes runtime. Safe visible branding has been corrected. Compatibility identifiers remain deliberately because an immediate rename would break existing settings, IPC calls, installed profiles, tests, and update paths.

## Completed low configuration work

- Use Keprix in onboarding, boot, update, connection, notification, terminal, error, About, and messaging copy.
- Point the About release link and onboarding documentation at the Keprix repository.
- Remove visible Nous Research ownership copy from the native About panel.
- Keep current tests and TypeScript checks passing.
- Preserve existing installations by retaining legacy protocol and storage aliases.

## Critical blocker to public desktop independence

The packaged first launch bootstrap still downloads an installer from the upstream NousResearch Hermes repository. The desktop also expects a Hermes compatible Python module and command in several runtime probes. A public Keprix package must not depend on an upstream mutable installer.

This is a code and release artifact task, not an owner credential task. It should be completed before the desktop is called market ready.

## Required implementation sequence

1. Publish a versioned Keprix bootstrap asset from the Keprix release workflow, with SHA256 checksums and signatures.
2. Change first launch bootstrap to use the pinned Keprix asset. Fail closed when its digest or signature does not match.
3. Package or install the Keprix backend entry point and probe it first. Keep the old Hermes entry point as a temporary fallback for one compatibility window.
4. Make `KEPRIX_HOME` and `KEPRIX_*` variables primary. Read equivalent `HERMES_*` variables only as deprecated aliases and never write new legacy values.
5. Introduce `window.keprixDesktop` and `keprix:` IPC names. Support old names as forwarding aliases for one migration window.
6. Dual read desktop storage keys. Migrate values atomically to `keprix.*`, record the migration version, and retain rollback-safe reads for one release.
7. Rename internal TypeScript types and modules mechanically only after the protocol bridge is tested. Internal names do not affect users, so correctness takes priority.
8. Replace or vendor the inherited UI package under a Keprix-owned package namespace with its licence notices preserved.
9. Remove upstream release URLs and network fetches through an automated source scan in CI.
10. Test clean install, upgrade, downgrade, uninstall, offline launch, local backend, remote sidecar, Windows, macOS, and Linux packages.

## Acceptance gates

- A clean machine installs and launches without contacting a NousResearch URL.
- User-visible desktop and TUI copy contains no Hermes or Nous branding.
- Existing users retain profiles, projects, sessions, credentials, and settings after upgrade.
- Keprix release assets are pinned and verified before execution.
- Desktop typecheck, platform tests, UI tests, build, and package smoke tests pass.
- CI fails if a new upstream bootstrap URL or user-facing legacy brand string is introduced.

## Owner configuration reserved

Only release signing, platform notarization, package repository publishing, and store credentials require owner configuration. Keep those values in `/opt/lampp/htdocs/verlox/.access/` and enter them through the approved GUI or CI secret settings. Never put them in source code.
