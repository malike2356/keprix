# Keprix - Prompt 267: Extension architecture (Keprix variant)

**Status:** Shipped core (`extensions/base.py`, `discovery.py`, `compatibility.py`, `lifecycle.py`, `config_merger.py`, `isolation.py`, `registry.py`, `extensions/scout/`, `upgrade/manifest.py` for `keprix.yaml`, `tests/extensions/*`; 32 tests passing). Discovery uses Python entry points (`keprix.extensions`) plus `KEPRIX_ACTIVE_EXTENSIONS`; not the yaml-path `ExtensionLoader` from this prompt. Deferred: `extensions/hooks.py` invoke hooks (`pre_invoke`, `post_invoke`, tool hooks), `keprix extension` CLI subcommands, `extensions/base-product/` template, feature-discovery subcommands.

**Note:** Prompt body is **Prompt 84** (extended Keprix variant). Canonical queue number is **267** per filename. Overlaps `265-extension-architecture-carina-variant.md`. Do not confuse with Chase **267** video ingest (`267-video-ingest-skill-pack.md`).

---

# Prompt 84; Keprix Extension Architecture: Products as Plugins, Not Forks

## Summary

Products (AbbiS, Petraclus, FleetZ, etc.) are separate repos that depend on `keprix` as a pip package. They register via `pyproject.toml` entry points (`keprix.extensions`) or bundled manifests under `KEPRIX_ACTIVE_EXTENSIONS` (e.g. scout).

## Shipped in Keprix

| Module | Purpose |
| --- | --- |
| `extensions/base.py` | `KeprixExtension` ABC, compatibility hook |
| `extensions/discovery.py` | Entry-point discovery, conflict validation |
| `extensions/compatibility.py` | Semver min-version and feature gates |
| `extensions/lifecycle.py` | Ordered startup/shutdown, route mount helpers |
| `extensions/config_merger.py` | Deep-merge product config |
| `extensions/isolation.py` | Cross-product import enforcement |
| `extensions/registry.py` | Runtime manifest registry, startup/shutdown hooks |
| `extensions/scout/` | Optional governance extension example |
| `upgrade/manifest.py` | Parse `keprix.yaml` for upgrade/check/lockfile (270-274) |
| `api/server.py` | `load_active_extensions()`, hook lifecycle on boot |

## Deferred from this prompt

- `extensions/loader.py`; yaml manifest discovery on disk (upgrade uses `keprix.yaml` separately)
- `extensions/manifest.py`; full `ExtensionManifest.from_yaml()` with feature blocks
- `extensions/hooks.py`; `pre_invoke`, `post_invoke`, `pre_tool_call`, `post_tool_call`
- `cli/extensions.py`; `keprix extension <product> feature enable|available`
- `extensions/base-product/`; bundled template repo
- `docs/extensions.md`; operator guide (not yet in `marketing/docs`)

## Product manifest (`keprix.yaml`)

Products ship a manifest with `product`, `keprix` version bounds, and `features` gates. Parsed by `upgrade/manifest.py` for compatibility checks during `keprix upgrade`. Example shape:

```yaml
manifest_version: "1.0"
product:
  name: "AbbiS"
  slug: "abbis"
  version: "1.2.0"
keprix:
  min_version: "0.3.0"
  tested_against: "0.6.0"
  incompatible_with: []
features:
  billing: { enabled: true }
  governance: { enabled: true }
  personas:
    - name: "Closer"
      class: "abbis.personas.sales_closer:EnterpriseCloser"
```

## Boot flow (as implemented)

1. Server starts; `load_active_extensions()` reads `KEPRIX_ACTIVE_EXTENSIONS`
2. Extension manifests load from `keprix.extensions.<name>.manifest`
3. `start_extension_hooks()` runs startup hooks (governance worker when enabled)
4. Product extensions via entry points use `ExtensionDiscovery` + `ExtensionLifecycle` in tests; full server wiring for all entry-point products is incremental

## Upgrade bridge (Prompt 270+)

```bash
pip install --upgrade keprix
keprix upgrade --check
keprix upgrade --dry-run
keprix upgrade --to 0.7.0
```

Products pin `keprix>=0.3,<1.0` in `pyproject.toml` and record `tested_against` in `keprix.yaml`.

## Verification (core)

- [x] `KeprixExtension` base class with lifecycle and compatibility
- [x] Entry-point discovery with incompatible-version skip
- [x] Extension conflict detection (duplicate names)
- [x] Config deep-merge and conflict validation
- [x] Product isolation rules
- [x] Lifecycle startup/shutdown ordering
- [x] Scout optional extension via `KEPRIX_ACTIVE_EXTENSIONS=scout`
- [x] `keprix.yaml` parsing for upgrade system
- [x] 32 tests in `tests/extensions/`
- [ ] Full `keprix extension` CLI feature matrix from this prompt
- [ ] Invoke-time hooks (`pre_invoke`, `post_invoke`, tool hooks)

## Related prompts

- `265-extension-architecture-carina-variant.md`; core architecture (Prompt 84)
- `270-274`; upgrade system using `keprix.yaml`
- Chase `267-272`; unrelated video ingest / tools adoption series
