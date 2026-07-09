# Config-driven product extensions

Keprix core does not hardcode vertical product names. Enable optional product packs via configuration when you extend a self-hosted deployment.

## Quick start

1. Copy the example registry:

```bash
cp config/products.example.yaml config/products.yaml
```

2. Enable one or more products:

```bash
export KEPRIX_ENABLED_PRODUCTS=scout
# or per-product env flag from your registry entry
export SCOUT_ENABLED=true
```

3. Optional: override config path:

```bash
export KEPRIX_PRODUCTS_CONFIG=/path/to/products.yaml
```

4. Restart the API so `load_products_config()` runs at startup.

## Product entry fields

| Field | Purpose |
| --- | --- |
| `display_name` | Human label |
| `env_flag` | Env var that enables product when `true` |
| `extension_name` | Links to `KEPRIX_ACTIVE_EXTENSIONS` |
| `audit_domain_pack` | Default `domain_pack` for review gateway audit events |
| `domain_packs` | Domain pack IDs loaded for workspaces |
| `domain_intents` | YAML files under `config/domain_intents/` |
| `glossaries` | YAML files under `config/domain_glossaries/` |
| `playbook_localization` | YAML under `config/playbook_localization/` |
| `voice_categories` | YAML under `config/voice_categories/` |
| `regulated_domains` | Domains requiring stricter localization review |
| `feature_flags` | Merged into UI contract `feature_flags` |

## Extensions vs products

- **Extensions** (`src/keprix/extensions/<name>/manifest.py`): code routes, hooks, governance providers.
- **Products** (`config/products.yaml`): declarative assets, feature flags, audit defaults.

A product may reference an extension via `extension_name: scout`.

## Review gateway

Pass `domain_pack` when creating a review request. If omitted, the enabled product's `audit_domain_pack` is used.

## Tests

```bash
PYTHONPATH=src python3 -m pytest tests/products/test_loader.py -q
```
