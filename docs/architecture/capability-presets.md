# Capability presets (declarative packs)

**Status:** Implemented (prompt 771, 2026-09-20)
**Package:** `keprix.capability_presets`
**Depends on:** capability seams (768), reversible plugin lifecycle (769)

## Intent

Replace ad-hoc env flag profiles with reviewable YAML **capability packs**.
Apply mounts/unmounts through 769 so switching `coding` → `crm` → `sidecar`
is reversible. Steal the DeepSeek Harness preset *idea*; do not import Cordis.

## Shipped presets

| Name | Intent | Seams | Soft Wall |
| --- | --- | --- | --- |
| `coding` | Dev / local tools | `policy:fs.local`, `policy:shell.local` | standard |
| `crm` | CRM / contacts; no broad shell | local fs, **sandboxed** shell | strict |
| `sidecar` | Narrow embed/sidecar | **sandboxed** fs + shell | strict |

Pack files: `src/keprix/capability_presets/packs/*.yaml`.

## Schema (fail closed)

Required: `name`, `soft_wall.profile` in `{standard, strict}`.

Forbidden:

- `soft_wall.profile` in `{off, disabled, none, bypass, yolo}`
- `soft_wall.require_approval: false`
- `env` / `env_overlays` with values (use `env_refs` key names only)
- Unknown seam ids
- Unknown plugin ids when `unknown_plugins: fail` (default)

Optional: `plugins`, `skills`, `declared_tools`, `seams`, `notes`.

## Apply behaviour

1. Diff against currently active preset.
2. Unmount previous `preset:<name>` declared tools via 769.
3. Disable plugins removed by the diff.
4. Mount plugins added (fail closed if unknown).
5. Activate seam Providers (registers sandboxed providers if needed).
6. Register new declared marker tools under synthetic plugin id `preset:<name>`.
7. Persist active state under `{KEPRIX_HOME}/capability_presets/active.json`.

## CLI

```bash
keprix presets list
keprix presets show coding
keprix presets apply coding
keprix presets apply crm
keprix presets diff crm --from coding
keprix presets active
```

## API

`/api/capability-presets` list / show / apply / diff / active.

## Authoring a custom pack

1. Write YAML matching the schema (see shipped packs).
2. Place under `~/.keprix/capability_presets/<name>.yaml` (user overrides bundled).
3. `keprix presets apply <name>`.

Do **not** put secrets in the file. Reference env key names via `env_refs` only.

## First-class modules (not plugins)

Packs must not turn these into plugins:

- Playbooks
- Billing
- Document Vault
- Channel Shield
- CRM product core (the `crm` preset only adds profile/seams around it)

## Soft Wall

A pack **cannot** disable Soft Wall. After apply, hardline still blocks
catastrophic shell commands on the active shell Provider.

## Related

- `docs/architecture/capability-seams.md`
- `docs/architecture/reversible-plugin-lifecycle.md`
