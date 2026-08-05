# Keprix - Prompt 77: De-Brand; Remove Hard-Coded Product Names, Make Keprix Generic

## Context

Keprix's source code currently contains hard-coded references to specific products (Scout, Carina, Petraclus, AbbiS, Fleetz, NHS). These product names appear in config constants, module names, import paths, route registrations, server startup, and comments throughout the codebase.

This is wrong. Keprix is the agent OS; a generic platform. Products built on Keprix (Petraclus, AbbiS, etc.) are distributions that extend it. Keprix should have zero awareness of what products run on top of it.

This prompt removes all hard-coded product names and replaces them with a generic extension system where products register themselves at runtime.

## Working Directory

`/opt/lampp/htdocs/verlox/keprix/`

## Problem Inventory

### 1. Hard-Coded URLs and Names in `config/constants.py`

```python
# CURRENT (WRONG):
SPONSOR_NAME = "Carina"
SPONSOR_URL = "https://carinaai.uk"
SCOUT_CONNECTOR_URL = "https://labyrinthscout.com"
```

### 2. Scout Deeply Embedded in Core

The `scout/` module is not a plug-in; it's woven into:
- `api/server.py`; imports scout router, starts/stops scout worker
- `api/conversation_routes.py`; imports scout kill relay
- `api/admin_workspace_routes.py`; scout licence key fields
- `evidence_pack/`; multiple files import scout modules directly
- `review_gateway/dispatch.py`; imports scout clinical events
- `typed_agents/deps_factory.py`; SCOUT_ENABLED env check

### 3. Product References in Comments, Strings, and Imports

- `research_workspace/`; carina references in templates
- `gateway/slash/`; product names in help text
- `extraction/scanner.py`; product name patterns
- `agents/self_config_agent.py`; product-specific config
- `interfaces/`; product mentions in channel adapters
- `personas/ember/coach.py`; references to other personas by product context

## Changes Required

### Phase 1: Config Constants; Genericise

```python
# NEW (CORRECT):
PRODUCT_NAME = "Keprix"
PRODUCT_VERSION = "0.1.0"
EDITION = "community"
HOMEPAGE = "https://keprix.io"
DOCS_URL = "https://keprix.io/docs"
GITHUB_URL = "https://github.com/malike2356/keprix"
DEVELOPER_IDENTITY_DIR = "~/.keprix/identity"
DEVELOPER_CONFIG_DIR = "~/.keprix"
DATA_DIR = "/data/keprix"

# Extension points; set by products at registration time, never hard-coded
EXTENSION_REGISTRY: dict[str, ExtensionManifest] = {}

# No hard-coded sponsor or connector URLs
# Products register their own URLs via the extension system
```

### Phase 2: Rename `scout/` → `governance/`; Make It Generic

The `scout/` module implements governance features (kill switch, audit, policy, evidence packs). These are generic governance capabilities; not Scout-specific. The Scout product is ONE implementation of governance. Other products may implement their own governance.

```text
RENAME:
  src/keprix/scout/          → src/keprix/governance/
  scout/routes.py            → governance/routes.py
  scout/kill_relay.py        → governance/kill_relay.py
  scout/worker.py            → governance/worker.py
  scout/store.py             → governance/store.py
  scout/config.py            → governance/config.py
  scout/client.py            → governance/client.py
  scout/clinical_events.py   → governance/audit_events.py
  scout/clinical_store.py    → governance/audit_store.py
  scout/policy_receiver.py   → governance/policy_receiver.py
  scout/enrollment.py        → governance/enrollment.py
  scout/event_reporter.py    → governance/event_reporter.py
  scout/heartbeat.py         → governance/heartbeat.py
  scout/signing.py           → governance/signing.py
  scout/models.py            → governance/models.py

UPDATE ALL IMPORTS:
  from keprix.scout.X   → from keprix.governance.X
  SCOUT_ENABLED          → GOVERNANCE_ENABLED
  KEPRIX_SCOUT_ENABLED   → KEPRIX_GOVERNANCE_ENABLED
```

### Phase 3: Create Extension System

```python
# src/keprix/extensions/__init__.py

@dataclass
class ExtensionManifest:
    """A product that extends Keprix."""
    name: str                    # e.g., "petraclus", "abbis"
    display_name: str            # e.g., "Petraclus"
    version: str
    homepage: str | None
    routes: list[APIRouter]      # FastAPI routers to register
    startup_hooks: list[Callable] # Functions to call on server start
    shutdown_hooks: list[Callable]
    governance_provider: str | None  # "scout", "native", None
    billing_provider: str | None     # "stripe", None
    feature_flags: dict[str, bool]
```

### Phase 4: Product Registration

Products register at startup via environment or config:

```python
# Config file or env:
KEPRIX_ACTIVE_EXTENSIONS = "petraclus,abbis"

# Each extension loads its manifest from:
# src/keprix/extensions/petraclus/manifest.py
# src/keprix/extensions/abbis/manifest.py

# At server startup:
for ext_name in active_extensions:
    manifest = load_extension_manifest(ext_name)
    register_extension(manifest)
```

### Phase 5: Update All Hard-Coded References

| File | Current | Replace With |
|------|---------|--------------|
| `api/server.py` | `from keprix.scout.routes import router as scout_router` | `from keprix.extensions.registry import get_governance_router` |
| `api/server.py` | `start_scout_worker()` | `start_governance_worker()` |
| `api/conversation_routes.py` | `from keprix.scout.kill_relay import agent_stop_requested` | `from keprix.governance.kill_relay import agent_stop_requested` |
| `api/admin_workspace_routes.py` | `scout_license_key`, `scout_audit_policy_url` | `governance_config` (generic dict) |
| `evidence_pack/generator.py` | `from keprix.scout.clinical_events` | `from keprix.governance.audit_events` |
| `typed_agents/deps_factory.py` | `scout_enabled` | `governance_enabled` |
| `review_gateway/dispatch.py` | `from keprix.scout.clinical_events` | `from keprix.governance.audit_events` |
| `config/constants.py` | `SPONSOR_URL`, `SCOUT_CONNECTOR_URL` | Remove entirely; products register their own URLs |
| `research_workspace/` | "Carina" in templates | Generic placeholder: "your analysis platform" |
| `gateway/slash/` | Product names in help text | Generic: "this workspace" |
| `personas/ember/coach.py` | References to specific personas by name | Use persona registry, not hard-coded names |
| `backend/builder/verlox_index.py` | "verlox" in filename and content | Rename to `keprix_index.py`, remove company-specifics |

### Phase 6: Environment Variable Cleanup

```bash
# REMOVE:
KEPRIX_SCOUT_ENABLED
CARINA_API_KEY
PETRACLUS_LICENSE

# REPLACE WITH:
KEPRIX_GOVERNANCE_ENABLED=true
KEPRIX_GOVERNANCE_PROVIDER=scout  # or "native"
KEPRIX_ACTIVE_EXTENSIONS=petraclus,abbis
```

## Verification Checklist

- [ ] No product name (Petraclus, AbbiS, Fleetz, NHS, Carina, Aiva, Scout, Verlox) appears in `src/keprix/` except in `extensions/` directory
- [ ] `scout/` directory renamed to `governance/` and all imports updated
- [ ] `config/constants.py` contains zero hard-coded product URLs
- [ ] Extension registration system works: products load manifest, routes register, hooks fire
- [ ] Server starts without Scout-specific imports; governance is optional
- [ ] Governance disabled by default, enabled via `KEPRIX_GOVERNANCE_ENABLED=true`
- [ ] All tests pass after renames
- [ ] `grep -r "petraclus\|abbis\|carina\|aiva\|scout" src/keprix/` returns zero results outside `extensions/`
- [ ] Documentation updated to reflect generic platform, not product-specific
