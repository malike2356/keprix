# Prompts 608-611: terminal, desktop, and lifecycle parity

**Status:** PENDING
**Depends on:** 600-602

## Prompt 608: terminal release parity

Create a machine-readable feature registry that maps each launch-critical Keprix
module to TUI commands, screens, permissions, help, empty states, errors, and tests.
Include CRM workflows and visual summaries suitable for terminals, datasets and
spreadsheet preprocessing, sidecars, approvals, channels, viCal, memory, research,
skills, plugins, settings, backup, updates, and diagnostics. A feature can be marked
TUI-supported only when a user can discover, execute, observe, cancel, retry, and
audit it without using the web UI.

Add keyboard-only, screen reader friendly text, narrow terminal, Unicode fallback,
offline, high-volume, long-session, slow stream, permission denial, and interrupted
upgrade tests. Preserve human approval gates and secret redaction. Generate command
reference docs from the registry to prevent drift.

## Prompt 609: desktop release parity and inherited identity removal

Audit every launch-critical module against the desktop app. Provide a parity matrix
and implement missing navigation, configuration, review, approvals, notifications,
visual CRM workflow, analytics, sidecars, data operations, diagnostics, update, and
support surfaces. Desktop may embed the hardened web surface where appropriate, but
authentication, deep links, file access, clipboard, notifications, and permissions
must follow explicit Electron security boundaries.

Remove or justify all inherited Hermes and Nous environment names, package names,
authors, app IDs, URLs, icons, update endpoints, support contacts, and legal text.
Keep compatibility aliases only where migration tests require them, with a removal
date. Synchronize desktop and backend versions.

## Prompt 610: signed desktop packaging matrix

Build clean packages for macOS arm64 and x64, Windows x64, and supported Linux
architectures. Use hardened Electron settings: context isolation, sandbox, no remote
module, narrow IPC schemas, validated external URLs, CSP, navigation guards, and
permission handlers. Sign Windows packages, sign and notarize macOS packages, and
verify signatures after download. If credentials are unavailable, produce clearly
labelled preview artifacts but block stable.

Test DMG install and removal, NSIS or MSI install and removal, AppImage, deb, rpm,
first boot, backend discovery, bundled or remote runtime selection, deep links,
sleep and resume, proxy, firewall, Unicode paths, non-admin accounts, upgrades,
crash recovery, and preservation or removal of user data by explicit choice.

## Prompt 611: updater, migration, backup, rollback, uninstall

Implement signed update feeds with stable, beta, and development channels. Never
allow downgrade or update across incompatible data schemas without a verified plan.
Before mutation, run preflight, create a restorable backup, show release notes and
permissions changes, and obtain consent. Support resumable downloads, signature
verification, rollback to the previous compatible version, and recovery mode.

Uninstall must distinguish program files, caches, logs, credentials, models, and
user-created data. Default to preserving user data. Add export, backup validation,
restore drills, interrupted migration, disk-full, corrupt backup, and old-version
fixtures to CI.
