# Keprix - Prompt 84: Extension Architecture; Products as Plugins, Not Forks

## Context

Products built on Keprix (Petraclus, AbbiS, Fleetz, NHS) must NOT be forks of the Keprix codebase. They must be extensions; separate repositories that depend on Keprix as a library. This prompt defines the architecture that makes this possible.

## The Problem

```
CURRENT (forking):
  abbis/                    ← copy of keprix v0.3 + abbis code
  petraclus/                ← copy of keprix v0.2 + petraclus code
  
  Result: 3 separate codebases. Keprix upgrade = manual merge × 3. Nightmare.

TARGET (extension):
  abbis/                    ← own repo, depends on keprix>=0.3
  petraclus/                ← own repo, depends on keprix>=0.3
  keprix/                   ← library, pip-installable
  
  Result: 1 core codebase. Products import from keprix. Upgrade = pip install --upgrade.
```

## Architecture

```
┌──────────────────────────────────────────────────────┐
│  ABBIS (product)                                     │
│  ─────────────────────────────────────────────────── │
│  abbis/pyproject.toml:                               │
│    dependencies = ["keprix>=0.3,<0.5"]               │
│                                                      │
│  abbis/src/abbis/                                    │
│    __init__.py                                       │
│    extension.py        # AbbiSExtension(KeprixExt)   │
│    domain/             # Borehole-specific code      │
│    ui/                 # AbbiS-specific UI           │
│                                                      │
│  Imports:                                            │
│    from keprix.agent import Agent                    │
│    from keprix.billing import SubscriptionManager    │
│    from keprix.providers import ComboEngine           │
└──────────────────────────────────────────────────────┘
                         │
                         │ pip install keprix
                         ▼
┌──────────────────────────────────────────────────────┐
│  KEPRIX (platform)                                   │
│  ─────────────────────────────────────────────────── │
│  keprix/pyproject.toml:                              │
│    name = "keprix"                                   │
│    version = "0.3.0"                                 │
│                                                      │
│  keprix/src/keprix/                                  │
│    agent/             # Agent engine                 │
│    providers/         # Provider routing             │
│    billing/           # SaaS billing                 │
│    governance/        # Governance                  │
│    extensions/        # Extension system ← NEW       │
│    integrations/      # Notion, etc.                 │
└──────────────────────────────────────────────────────┘
```

## Extension System

Products register as extensions. Keprix loads them at startup.

```python
# keprix/src/keprix/extensions/base.py

from abc import ABC, abstractmethod

class KeprixExtension(ABC):
    """Base class for any product built on Keprix."""
    
    # Identity
    name: str                    # "abbis", "petraclus"
    display_name: str            # "AbbiS", "Petraclus"
    version: str                 # "1.0.0"
    keprix_min_version: str      # "0.3.0"; minimum Keprix version
    
    # What this extension provides
    routes: list = []            # FastAPI routers
    domain_tools: list = []      # Domain-specific agent tools
    domain_packs: list = []      # Domain knowledge packs
    personas: list = []          # Product-specific personas
    skill_packs: list = []       # Product-specific skill packs
    ui_components: list = []     # React components to mount
    
    # What this extension consumes
    required_features: list[str] = []  # ["billing", "governance", "notion"]
    
    # Lifecycle
    @abstractmethod
    async def on_startup(self) -> None: ...
    
    @abstractmethod
    async def on_shutdown(self) -> None: ...
    
    def check_compatibility(self) -> CompatibilityResult:
        """Check if this extension is compatible with current Keprix."""
        from keprix.config.constants import PRODUCT_VERSION
        current = parse_version(PRODUCT_VERSION)
        minimum = parse_version(self.keprix_min_version)
        
        if current < minimum:
            return CompatibilityResult(
                compatible=False,
                reason=f"Requires Keprix >= {self.keprix_min_version}, running {PRODUCT_VERSION}",
            )
        
        # Check required features are available
        missing = [f for f in self.required_features if not feature_available(f)]
        if missing:
            return CompatibilityResult(
                compatible=False,
                reason=f"Missing required features: {missing}",
            )
        
        return CompatibilityResult(compatible=True)
```

## Product Structure Template

```text
abbis/
  pyproject.toml             # depends on keprix>=0.3
  README.md
  src/
    abbis/
      __init__.py
      extension.py           # AbbiSExtension(KeprixExtension)
      domain/
        borehole.py          # Borehole-specific domain logic
        groundwater.py       # Groundwater analysis
        geology.py           # Geological data processing
      ui/
        dashboard.py         # AbbiS dashboard
        well_monitor.py      # Well monitoring UI
      billing.yaml           # AbbiS pricing plans
      personas/
        geo_analyst.py       # Domain-specific persona
      tools/
        well_search.py       # Search borehole database
        water_quality.py     # Water quality analysis
  tests/
    test_extension.py
  config/
    abbis.env                # AbbiS environment variables
```

```toml
# abbis/pyproject.toml
[project]
name = "abbis"
version = "1.0.0"
requires-python = ">=3.11,<3.14"
dependencies = [
    "keprix>=0.3.0,<0.5.0",     # Compatible with Keprix 0.3.x and 0.4.x
]

[project.scripts]
abbis = "abbis.__main__:main"

[project.entry-points."keprix.extensions"]
abbis = "abbis.extension:AbbiSExtension"
```

## How Keprix Discovers Extensions

```python
# keprix/src/keprix/extensions/discovery.py

import importlib.metadata

class ExtensionDiscovery:
    """Discovers installed Keprix extensions via Python entry points."""
    
    def discover(self) -> list[KeprixExtension]:
        extensions = []
        
        # Discover via setuptools entry points
        entry_points = importlib.metadata.entry_points(group="keprix.extensions")
        for ep in entry_points:
            ext_class = ep.load()
            ext = ext_class()
            
            # Check compatibility
            compat = ext.check_compatibility()
            if not compat.compatible:
                logger.warning(f"Extension {ext.name} incompatible: {compat.reason}")
                continue
            
            extensions.append(ext)
            logger.info(f"Loaded extension: {ext.name} v{ext.version}")
        
        return extensions
    
    def validate_no_conflicts(self, extensions: list[KeprixExtension]) -> None:
        """Ensure no duplicate extension names or conflicting required features."""
        names = [e.name for e in extensions]
        if len(names) != len(set(names)):
            duplicates = [n for n in names if names.count(n) > 1]
            raise ExtensionConflictError(f"Duplicate extension names: {set(duplicates)}")
```

## Server Startup with Extensions

```python
# keprix/src/keprix/api/server.py (updated)

from keprix.extensions.discovery import ExtensionDiscovery

async def start_server():
    app = FastAPI()
    
    # Discover extensions
    discovery = ExtensionDiscovery()
    extensions = discovery.discover()
    
    # Register extension routes
    for ext in extensions:
        for route in ext.routes:
            app.include_router(route, prefix=f"/api/{ext.name}")
        
        # Register extension tools
        for tool in ext.domain_tools:
            tool_registry.register(tool)
        
        # Register extension UI components
        for component in ext.ui_components:
            ui_registry.register(component)
        
        # Call startup hook
        await ext.on_startup()
    
    logger.info(f"Started with {len(extensions)} extension(s): {[e.name for e in extensions]}")
```

## Product Isolation

Products NEVER import each other. AbbiS never imports from Petraclus. Isolation rules:

```
Done:  ALLOWED:
  abbis/src/abbis/domain/borehole.py:
    from keprix.agent import Agent           # Import from platform
    from keprix.billing import check_plan    # Import from platform

Failed:  FORBIDDEN:
  abbis/src/abbis/domain/borehole.py:
    from petraclus.tools.exploit import *    # NEVER import another product
  
  petraclus/src/petraclus/domain/cyber.py:
    from abbis.domain.borehole import *      # NEVER import another product
```

## Product Configuration

Each product brings its own config. Keprix merges them.

```yaml
# abbis/config/abbis.yaml; product-specific overrides
keprix:
  product_name: "AbbiS"
  
billing:
  product_id: "abbis"
  plans:
    - id: "starter"
      name: "Starter"
      price: 7900    # £79/month
      feature_flags:
        wells: 10
        reports: "basic"
    ...

notion:
  enabled: false     # AbbiS doesn't use Notion; uses its own well database

providers:
  combos:
    - id: "abbis_default"
      tiers:
        - id: "api_keys"
          providers: ["anthropic", "deepseek"]  # Prefer reasoning models for geology
```

## Files To Create

```text
keprix/src/keprix/extensions/
  __init__.py
  base.py               # KeprixExtension base class
  discovery.py          # Extension discovery via entry points
  compatibility.py      # Version compatibility checking
  isolation.py           # Product isolation enforcement
  config_merger.py       # Merge product config with Keprix config
  lifecycle.py           # Extension lifecycle management

keprix/config/
  extensions.example.yaml   # Example extension configuration

keprix/docs/
  extensions.md         # How to build a product on Keprix
  extension-template.md # Template for new product repos

tests/extensions/
  test_discovery.py
  test_compatibility.py
  test_isolation.py
  test_config_merger.py
  test_lifecycle.py
```

## Version Compatibility Contract

```
KEPRIX VERSIONING (Semantic; MAJOR.MINOR.PATCH):

  MAJOR bump (0.x → 1.x): BREAKING changes
    - API method signatures change
    - Config format changes incompatibly
    - Removed features
    → Products must update their code
    
  MINOR bump (0.3.x → 0.4.x): NEW features, backward-compatible
    - New modules added
    - New config options added (with defaults)
    - New extension hooks
    → Products get new features for free, no code changes
    
  PATCH bump (0.3.0 → 0.3.1): BUG FIXES only
    - No new features
    - No breaking changes
    → Products update automatically, zero risk

PRODUCT DEPENDENCY:
  abbis/pyproject.toml: "keprix>=0.3.0,<0.5.0"
    → Accepts 0.3.x and 0.4.x (all non-breaking)
    → Rejects 0.5.x (potential breaking changes)
    → Rejects 1.x (definite breaking changes)
```

## Verification

- [ ] Keprix installable via `pip install keprix`
- [ ] Product installable via `pip install abbis` (depends on keprix)
- [ ] Extension discovered at startup via entry points
- [ ] Compatibility check blocks incompatible Keprix versions
- [ ] Product routes mounted at `/api/abbis/*`
- [ ] Product tools registered in tool registry
- [ ] Product UI components mounted in UI shell
- [ ] Product isolation enforced (cross-product imports blocked)
- [ ] Product config merges with Keprix config without conflicts
- [ ] Two products can run simultaneously (Petraclus + AbbiS)
- [ ] Tests pass for all modules
