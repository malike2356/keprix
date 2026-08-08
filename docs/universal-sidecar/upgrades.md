# Upgrades

## Policy

Additive only within a major version. Breaking changes require a major bump and
a documented migration window. Deprecations emit `Deprecation` / `Sunset`
headers and appear in doctor/conformance reports.

## Procedure

1. Expand: install new contract/pack beside old.
2. Migrate: dry-run migrations; validate grants against product `/capabilities`.
3. Contract: remove old surfaces only after traffic drains.

Retain last-known-good pack. Support dry-run and rollback. Never auto-enable
newly risky capabilities.

## Provisioning (idempotent)

Verify compatibility, create namespace and keys, register identity and
callbacks, install pinned pack, apply migrations, register nodes/connectors,
smoke + isolation tests, activate feature flag after operator approval, emit
provision receipt (no secrets).
