# Hermes to Keprix rename inventory

This inventory is for the safe rename pass. It classifies remaining Hermes-era names so Keprix can finish the rename without breaking state, imports, tests, upstream attribution, or compatibility.

## Scan command

```bash
rg -n --hidden \
  --glob '!{.git,.venv,node_modules,frontend/node_modules,frontend/.next,frontend/public/guide,graphify-out}/**' \
  --glob '!**/__pycache__/**' \
  --glob '!**/*.pyc' \
  'Hermes|hermes|HERMES|\.hermes|hermes-agent|hermes_cli|ui-tui|tui_gateway' .
```

The raw scan is intentionally broad. The useful rename scope is first-party code, docs, tests, package metadata, Docker, Nix, desktop wrappers, installer scripts, and prompts. Vendored upstream reference trees and large third-party security datasets should not be mechanically renamed.

## Classification summary

| Classification | Current scope | Policy |
| --- | --- | --- |
| Rename now | User-facing Keprix copy, CLI help text, package metadata, root docs, Docker labels, default service names, desktop UI copy | Rename to Keprix unless it is explicitly describing upstream Hermes, a migration source, or a compatibility fallback. |
| Compatibility alias | `.hermes`, `HERMES_*`, `hermes_cli`, `hermes` executable probes, desktop bridge names, old MIME keys, old update remotes | Keep read compatibility. New writes and new UI should use Keprix names. |
| Upstream reference | `src/keprix/upstream/hermes_*`, adoption prompts, upstream monitor tests, Hermes parity docs | Keep Hermes names where the object is specifically the upstream project or an upstream feature record. |
| Legal attribution | `THIRD_PARTY_NOTICES.md`, `docs/community/acknowledgments.md`, licence and notice text | Keep intact. Do not rewrite legal attribution away from Hermes Agent or Nous Research. |
| Fixture or competitor reference | Migration tests, productization guards, archived prompts, competitor research paths | Keep unless a test is asserting new Keprix behavior. |
| Leave until package migration | Nix module names, Electron bridge API, desktop package internals, bundled gateway/TUI compatibility areas, generated plugin assets | Rename in a controlled migration prompt with aliases and tests. |

## Path inventory

| Area | Examples | Classification | Notes |
| --- | --- | --- | --- |
| Legal notices | `THIRD_PARTY_NOTICES.md`, `docs/community/acknowledgments.md` | Legal attribution | Required attribution. Preserve the upstream project name. |
| Architecture docs | `docs/architecture/core-product-boundary.md`, `docs/architecture/tui-freeze-and-parity.md` | Upstream reference | Keep where discussing Hermes as behavior reference. Avoid using Hermes as Keprix brand copy. |
| User docs | `docs/features/tui.md`, `docs/features/web-voice-input.md`, `docs/reference/cli.md`, security docs | Rename now | Replace user-facing Hermes copy unless comparing upstream behavior or migration sources. |
| Package metadata | `pyproject.toml`, `src/keprix/package.json`, `src/keprix/package-lock.json`, `src/keprix/MANIFEST.in` | Mixed | `hermes_inventory.yaml` is upstream monitor data. Workspace names like `ui-tui` should migrate with package scripts. |
| CLI runtime | `src/keprix/__main__.py`, `src/keprix/cli.py`, `src/keprix/keprix_cli/main.py`, `src/keprix/keprix_cli/doctor.py` | Rename now plus compatibility alias | Public command output should say Keprix. Doctor can mention old Hermes names only when reporting fallback state. |
| State and config | `src/keprix/.env.example`, `src/keprix/cli-config.yaml.example`, `src/keprix/keprix` | Compatibility alias | New state should use `.keprix` and `KEPRIX_*`. Old `.hermes` and `HERMES_*` remain readable. |
| Migration adapters | `src/keprix/backend/migration/adapters/hermes.py`, migration tests | Compatibility alias | This is intentionally a Hermes import adapter. Keep source names visible. |
| Upstream monitor | `src/keprix/upstream/hermes_monitor.py`, `hermes_adoption.py`, `hermes_inventory.yaml`, tests | Upstream reference | This code tracks Hermes releases by name. Do not rename the tracked upstream identity. |
| Security feature tracking | `src/keprix/security/hermes_features.py`, `tests/security/test_hermes_features.py` | Upstream reference | Keep until the feature tracker is generalized. |
| TUI and gateway parity | `src/keprix/tui/*`, `src/keprix/tests/tui_gateway/*`, `src/keprix/voice/gateway_handlers.py` | Mixed | Comments can mention ported behavior. Public API and module names should move to Keprix only during gateway package migration. |
| Nix | `src/keprix/nix/*.nix`, `src/keprix/flake.nix` | Leave until package migration | Rename service module from `services.hermes-agent` to a Keprix module with old option aliases. |
| Docker and services | `src/keprix/Dockerfile`, `src/keprix/docker/**`, root `docker/**` | Rename now plus compatibility alias | Container users, home dirs, s6 service names, and env files need migration tests. |
| Desktop app | `src/keprix/apps/desktop/**` | Leave until package migration | Electron bridge names like `window.hermesDesktop` need staged aliases before UI renaming. |
| Installer and packaging scripts | `src/keprix/scripts/**`, `src/keprix/packaging/**`, `scripts/**` | Rename now plus compatibility alias | Shell command examples should prefer Keprix. Legacy update and install paths need compatibility tests. |
| Tests and fixtures | `tests/**`, `src/keprix/tests/**` | Fixture or competitor reference | Rename tests only with the behavior they validate. Migration tests should keep Hermes fixture names. |
| Prompt library | `1st-plan/1st-prompt/**` | Fixture or competitor reference | Current and archived prompts can keep Hermes names as source material. New implementation prompts should state Keprix surface names. |

## Rename map

| Old name | New name | Compatibility rule |
| --- | --- | --- |
| `Hermes` in user-facing Keprix UI or CLI output | `Keprix` | Rename now unless it is legal attribution or upstream comparison. |
| `hermes` executable or service examples | `keprix` | Keep old command examples only in migration docs. |
| `hermes-agent` package/service label | `keprix` or `keprix-agent` | Nix and Docker should provide old aliases where they are config keys. |
| `HERMES_HOME` | `KEPRIX_HOME` | `KEPRIX_HOME` wins. Read `HERMES_HOME` only as fallback. |
| `.hermes` state directory | `.keprix` | New writes go to `.keprix`. Existing `.hermes` remains readable. |
| `HERMES_*` env vars | `KEPRIX_*` | New vars win. Old vars are fallback only. |
| `hermes_cli` import path | `keprix_cli` | Keep import shim until package migration is complete. |
| `ui-tui` workspace name | Keprix TUI package name | Rename with package scripts, lockfile, and desktop build tests together. |
| `tui_gateway` module | Keprix gateway module name | Rename with voice, desktop, gateway tests, and import aliases together. |
| `window.hermesDesktop` | `window.keprixDesktop` | Add the new bridge first, keep old bridge as alias, then update UI code. |
| `application/x-hermes-paths` | `application/x-keprix-paths` | Accept both MIME keys during drag and drop migration. |

## State directory policy

1. New state writes must prefer `KEPRIX_HOME` or the default `~/.keprix`.
2. If `KEPRIX_HOME` is unset and `HERMES_HOME` is set, read the old value as fallback.
3. If neither env var is set, read existing `~/.keprix` first, then existing `~/.hermes` for compatibility.
4. Migration must be idempotent. Running it repeatedly must not duplicate profiles, sessions, credentials, cache entries, or plugin links.
5. Migration must not delete `.hermes` automatically. Offer an explicit cleanup command after verification.
6. Doctor output should report when Keprix is using fallback `.hermes` state and recommend `keprix migrate state`.
7. Normal startup should stay quiet unless both old and new state exist with conflicting critical config.

## Environment variable policy

1. `KEPRIX_*` variables always win over matching `HERMES_*` variables.
2. `HERMES_*` fallback reads are allowed for one migration window and must be covered by tests.
3. Fallback warnings should be quiet during normal startup.
4. `keprix doctor` should show a compatibility section listing old variables that were read.
5. Docs should teach only `KEPRIX_*` names except in migration pages.
6. Config writers must persist `KEPRIX_*` names and must not create new `HERMES_*` values.

## Prompt 323 handoff

The next rename prompt should start with user-facing and package-facing names that do not require compatibility shims:

- Root docs and public feature docs.
- CLI help and non-legal user-facing strings.
- Package metadata that does not identify upstream Hermes monitor files.
- Tests that assert Keprix surface text.

The next prompt should defer these until dedicated migration work:

- Nix `services.hermes-agent` module.
- Docker users, service dirs, and persistent home paths.
- Electron bridge API.
- `hermes_cli` import shims.
- `tui_gateway` module path.
- `.hermes` state migration.
