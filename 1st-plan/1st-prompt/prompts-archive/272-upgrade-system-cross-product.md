# Keprix - Prompt 272: Cross-product upgrade (discovery, lockfile, adoption prompts)

**Status:** Shipped (`upgrade/discovery.py`, `lockfile.py`, expanded `prompts.py`, lockfile on execute, `tests/upgrade/`).

---

# Keprix - Prompt 85: Upgrade System; Keep Products Current Without Breaking

## Context

When Keprix gets new features, every product built on it must be able to upgrade safely. This prompt builds the upgrade infrastructure: compatibility checking, dry-run testing, automated migration, rollback, and upgrade prompts.

## The Upgrade Problem

```
Scenario:
  AbbiS v1.0 runs on Keprix 0.3.0
  Keprix gets: billing (0.4.0), OmniRoute routing (0.5.0), Notion (0.6.0)
  
  AbbiS wants billing and routing, but not Notion.
  Upgrade path: 0.3.0 → 0.5.0 (skip 0.4? go to 0.5?)
  
  Questions:
  - Will the upgrade break AbbiS?
  - Can we test before upgrading?
  - What if it does break; how to roll back?
  - How do we know what changed?
```

## Architecture

```
UPGRADE WORKFLOW:

  [Product admin runs: keprix upgrade --check]
       │
  ┌────▼──────────────────────────────────────────┐
  │  COMPATIBILITY CHECK                          │
  │  ──────────────────────────────────────────── │
  │  1. Read product's keprix version constraint  │
  │  2. Check if target version is compatible     │
  │  3. List new features available               │
  │  4. List breaking changes (if any)            │
  │  5. List deprecated features                  │
  │  6. Predict upgrade risk (LOW/MED/HIGH)       │
  └────┬──────────────────────────────────────────┘
       │  Risk: LOW → proceed
       │  Risk: MED → warn, suggest dry-run
       │  Risk: HIGH → block, must read migration guide
       ▼
  ┌──────────────────────────────────────────────┐
  │  DRY-RUN TEST                                │
  │  ──────────────────────────────────────────── │
  │  1. Spin up test environment with new Keprix  │
  │  2. Run product's test suite                 │
  │  3. Check extension compatibility            │
  │  4. Check config migration                   │
  │  5. Report: PASS/FAIL with details           │
  └────┬──────────────────────────────────────────┘
       │  PASS → proceed
       │  FAIL → review failures, fix or abort
       ▼
  ┌──────────────────────────────────────────────┐
  │  UPGRADE EXECUTION                           │
  │  ──────────────────────────────────────────── │
  │  1. Backup current state (config, DB, keys)  │
  │  2. pip install --upgrade keprix==<target>   │
  │  3. Run config migration (if needed)         │
  │  4. Run DB migration (Alembic)              │
  │  5. Verify extension loads correctly         │
  │  6. Health check endpoints                   │
  │  7. Log: "Upgraded from 0.3.0 to 0.5.0"     │
  └────┬──────────────────────────────────────────┘
       │  Success → done
       │  Failure → rollback
       ▼
  ┌──────────────────────────────────────────────┐
  │  ROLLBACK                                    │
  │  ──────────────────────────────────────────── │
  │  1. pip install keprix==<previous>           │
  │  2. Restore config from backup               │
  │  3. Rollback DB migration (Alembic downgrade)│
  │  4. Verify extension loads on old version    │
  │  5. Log: "Rolled back to 0.3.0"             │
  └──────────────────────────────────────────────┘
```

## Feature Discovery; What's New in This Version?

```python
# keprix/src/keprix/upgrade/discovery.py

class FeatureDiscovery:
    """Discovers what new features are available in a target version."""
    
    FEATURE_REGISTRY: dict[str, FeatureInfo] = {
        "0.4.0": [
            FeatureInfo(
                name="billing",
                description="Native SaaS billing with Stripe integration",
                module="keprix.billing",
                requires_config=True,
                breaking=False,
                prompts=["78"],
            ),
            FeatureInfo(
                name="governance",
                description="Generic governance layer (renamed from Scout)",
                module="keprix.governance",
                requires_config=False,
                breaking=True,  # scout/ renamed to governance/
                prompts=["77"],
                migration_guide="migrations/0.4.0-scout-to-governance.md",
            ),
        ],
        "0.5.0": [
            FeatureInfo(
                name="combo_routing",
                description="Smart provider routing with combos, quota, auto-fallback",
                module="keprix.providers.combo",
                requires_config=True,
                breaking=False,
                prompts=["79"],
            ),
            FeatureInfo(
                name="compression",
                description="RTK + Caveman token compression (15-95% savings)",
                module="keprix.providers.compression",
                requires_config=False,
                breaking=False,
                prompts=["80"],
            ),
            FeatureInfo(
                name="guardrails",
                description="PII masking, prompt injection defence",
                module="keprix.providers.guardrails",
                requires_config=False,
                breaking=False,
                prompts=["80"],
            ),
        ],
        "0.6.0": [
            FeatureInfo(
                name="notion",
                description="Notion workspace integration (6 MCP tools)",
                module="keprix.integrations.notion",
                requires_config=True,
                breaking=False,
                prompts=["83"],
            ),
            FeatureInfo(
                name="a2a",
                description="Agent-to-Agent protocol and task management",
                module="keprix.providers.a2a",
                requires_config=False,
                breaking=False,
                prompts=["81"],
            ),
            FeatureInfo(
                name="observability",
                description="Real-time dashboards, spend tracking, route explain",
                module="keprix.providers.observability",
                requires_config=False,
                breaking=False,
                prompts=["81", "82"],
            ),
        ],
    }
    
    def get_new_features(self, from_version: str, to_version: str) -> list[FeatureInfo]:
        """Get all new features between two versions."""
        features = []
        for version, version_features in self.FEATURE_REGISTRY.items():
            if parse_version(from_version) < parse_version(version) <= parse_version(to_version):
                features.extend(version_features)
        return features
    
    def get_breaking_changes(self, from_version: str, to_version: str) -> list[FeatureInfo]:
        """Get breaking changes between two versions."""
        return [f for f in self.get_new_features(from_version, to_version) if f.breaking]
    
    def get_opt_in_features(self, from_version: str, to_version: str) -> list[FeatureInfo]:
        """Get features that require explicit config to enable."""
        return [f for f in self.get_new_features(from_version, to_version) if f.requires_config]
```

## Compatibility Check Command

```bash
# CLI command:
$ keprix upgrade --check --to 0.5.0

Output:
═══════════════════════════════════════════════════════
  KEPRIX UPGRADE CHECK
  ────────────────────────────────────────────────────
  Product:     AbbiS v1.0.0
  Current:     Keprix 0.3.0
  Target:      Keprix 0.5.0
  Risk:        MEDIUM (1 breaking change)
  
  NEW FEATURES (4):
  Done:  billing         SaaS billing with Stripe [requires config]
  Done:  combo_routing   Smart provider routing [requires config]
  Done:  compression     Token compression 15-95% [opt-in]
  Done:  guardrails      PII masking, injection defence [opt-in]
  
  BREAKING CHANGES (1):
  WARNING:   governance      scout/ module renamed to governance/
     → Migration guide: migrations/0.4.0-scout-to-governance.md
     → Product code referencing 'keprix.scout' must be updated
  
  ACTIONS REQUIRED:
  1. Update imports: keprix.scout → keprix.governance
  2. Set KEPRIX_BILLING_ENABLED=true and add billing.yaml
  3. Configure combo routing in combos.yaml
  4. Optionally enable compression and guardrails
  
  DRY-RUN: keprix upgrade --dry-run --to 0.5.0
  
═══════════════════════════════════════════════════════
```

## Dry-Run Test

```bash
$ keprix upgrade --dry-run --to 0.5.0

Output:
═══════════════════════════════════════════════════════
  DRY-RUN UPGRADE TEST
  ────────────────────────────────────────────────────
  
  [1/4] Setting up test environment with Keprix 0.5.0... 
  [2/4] Running AbbiS test suite (247 tests)...  (all passed)
  [3/4] Checking extension compatibility... 
  [4/4] Checking config migration... 
  
  RESULT: PASS; Upgrade is safe to apply.
  
  Estimated downtime: < 30 seconds
  Rollback available: yes (keprix upgrade --rollback)
  
═══════════════════════════════════════════════════════
```

## Upgrade Execution

```bash
$ keprix upgrade --to 0.5.0

Output:
═══════════════════════════════════════════════════════
  UPGRADE IN PROGRESS
  ────────────────────────────────────────────────────
  
  [1/6] Backing up current state...  (saved to .keprix/backups/2026-07-08/)
  [2/6] Installing Keprix 0.5.0... 
  [3/6] Running config migration...  (2 configs updated)
  [4/6] Running DB migrations...  (3 migrations applied)
  [5/6] Verifying extension loads... 
  [6/6] Health check...  (all endpoints healthy)
  
  UPGRADE COMPLETE
  ────────────────────────────────────────────────────
  Keprix:  0.3.0 → 0.5.0
  Duration: 28 seconds
  Downtime: 12 seconds
  
  NEW FEATURES AVAILABLE:
  - billing: Set KEPRIX_BILLING_ENABLED=true to enable
  - combo_routing: Add providers to combos.yaml
  - compression: Set KEPRIX_COMPRESSION_ENABLED=true (opt-in)
  - guardrails: Set KEPRIX_GUARDRAILS_ENABLED=true (opt-in)
  
  If anything breaks: keprix upgrade --rollback
  
═══════════════════════════════════════════════════════
```

## Upgrade Prompt System

When a new Keprix version adds features, an upgrade prompt is published that products can run to adopt the new feature:

```python
# keprix/src/keprix/upgrade/prompts.py

class UpgradePrompt:
    """A prompt that guides a product through adopting a new Keprix feature."""
    
    name: str                    # "adopt-billing"
    version: str                 # "0.4.0"
    description: str             # "Add SaaS billing to your product"
    target_product: str          # "any" or "petraclus", "abbis"
    
    # What to check before running
    pre_checks: list[Check] = []
    
    # What to do
    steps: list[UpgradeStep] = []
    
    # What to verify after
    post_checks: list[Check] = []
```

```bash
# List available upgrade prompts:
$ keprix upgrade --list-prompts

AVAILABLE UPGRADE PROMPTS:
  adopt-billing (0.4.0)     Add SaaS billing with Stripe
  adopt-combo-routing (0.5.0) Smart provider routing
  adopt-compression (0.5.0)  Token compression (opt-in)
  adopt-guardrails (0.5.0)   PII masking & injection defence
  adopt-notion (0.6.0)       Notion workspace integration
  adopt-a2a (0.6.0)          Agent-to-Agent protocol

# Run a specific upgrade prompt:
$ keprix upgrade --prompt adopt-billing

Output:
═══════════════════════════════════════════════════════
  UPGRADE PROMPT: adopt-billing
  ────────────────────────────────────────────────────
  
  [1/5] Checking prerequisites...  (STRIPE_SECRET_KEY set)
  [2/5] Adding billing.yaml to config... 
  [3/5] Running billing migration... 
  [4/5] Testing Stripe connection... 
  [5/5] Verifying feature gates... 
  
  DONE! Billing is now available.
  - Customer portal: /api/billing/portal
  - Stripe dashboard: https://dashboard.stripe.com
  
═══════════════════════════════════════════════════════
```

## Migration Guides

Every breaking change ships with a migration guide:

```markdown
# migrations/0.4.0-scout-to-governance.md

## Breaking Change: scout/ → governance/

### What Changed
The `keprix.scout` module has been renamed to `keprix.governance`.
Scout is now a product that connects via the governance layer,
not a core module.

### What You Must Update

1. **Import changes:**
   OLD: from keprix.scout.kill_relay import agent_stop_requested
   NEW: from keprix.governance.kill_relay import agent_stop_requested

2. **Environment variables:**
   OLD: KEPRIX_SCOUT_ENABLED=true
   NEW: KEPRIX_GOVERNANCE_ENABLED=true

3. **Config changes:**
   OLD: scout_license_key: "xxx"
   NEW: governance: { provider: "scout", license_key: "xxx" }

### Automated Migration
Run `keprix upgrade --migrate scout-to-governance`
This will automatically update imports and config.
```

## Rollback

```bash
$ keprix upgrade --rollback

Output:
═══════════════════════════════════════════════════════
  ROLLBACK IN PROGRESS
  ────────────────────────────────────────────────────
  
  [1/4] Restoring Keprix 0.3.0... 
  [2/4] Restoring config from backup... 
  [3/4] Rolling back DB migrations... 
  [4/4] Verifying extension loads on 0.3.0... 
  
  ROLLBACK COMPLETE; Running Keprix 0.3.0
  
═══════════════════════════════════════════════════════
```

## Version Lock File

Each product maintains a lock file recording its Keprix version and which features are enabled:

```yaml
# abbis/.keprix-lock.yaml
product: abbis
product_version: 1.0.0
keprix_version: 0.5.0
installed_at: "2026-07-08T22:00:00Z"
last_upgrade_at: "2026-07-08T22:15:00Z"
last_upgrade_from: "0.3.0"

features:
  billing: { enabled: true, version: "0.4.0" }
  governance: { enabled: true, version: "0.4.0", provider: "native" }
  combo_routing: { enabled: true, version: "0.5.0" }
  compression: { enabled: false }
  guardrails: { enabled: false }
  notion: { enabled: false }
  a2a: { enabled: false }
  observability: { enabled: true, version: "0.5.0" }

backups:
  - path: ".keprix/backups/2026-07-08/"
    version: "0.3.0"
    created_at: "2026-07-08T22:14:00Z"
```

## Files To Create

```text
keprix/src/keprix/upgrade/
  __init__.py
  checker.py             # Compatibility checker
  discovery.py            # Feature discovery per version
  executor.py             # Upgrade execution engine
  rollback.py             # Rollback engine
  dry_run.py              # Dry-run test runner
  prompts.py              # Upgrade prompt system
  lockfile.py             # Version lock file management
  backup.py                # State backup before upgrade
  
keprix/src/keprix/keprix_cli/
  upgrade.py              # 'keprix upgrade' CLI command

keprix/migrations/
  upgrade/                 # Upgrade-specific migration guides
    0.4.0-scout-to-governance.md
    0.5.0-billing-opt-in.md
    0.6.0-notion-opt-in.md

keprix/docs/
  upgrading.md            # Upgrade guide for product maintainers
  version-policy.md       # Version compatibility policy
  release-checklist.md    # What to include in each release

tests/upgrade/
  test_checker.py
  test_executor.py
  test_rollback.py
  test_dry_run.py
  test_lockfile.py
  test_prompts.py
```

## Verification

- [ ] `keprix upgrade --check` shows compatible versions and new features
- [ ] `keprix upgrade --check` blocks upgrades with breaking changes
- [ ] `keprix upgrade --dry-run` runs product test suite against new version
- [ ] Dry-run reports PASS/FAIL with specific failure details
- [ ] `keprix upgrade --to X.Y.Z` executes upgrade with backup → install → migrate → verify
- [ ] `keprix upgrade --rollback` restores previous version with zero data loss
- [ ] `keprix upgrade --list-prompts` shows available upgrade prompts
- [ ] `keprix upgrade --prompt adopt-billing` runs guided feature adoption
- [ ] Automated migration updates imports and config for breaking changes
- [ ] Lock file records current version and enabled features
- [ ] Backup contains all state needed for rollback
- [ ] Upgrading from 0.3 → 0.5 skips intermediate versions correctly
- [ ] Two products on same machine can run different Keprix versions (via virtualenvs)
- [ ] Tests pass for all modules
