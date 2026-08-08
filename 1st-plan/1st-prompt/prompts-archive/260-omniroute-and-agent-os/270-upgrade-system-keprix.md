# Keprix - Prompt 270: Upgrade system (check, plan, migrate, rollback)

**Status:** Shipped (`src/keprix/upgrade/`, `keprix upgrade` CLI, `tests/upgrade/`; 52+ tests at archive time).

---

# Prompt 85; Keprix Upgrade System: Safe, Guided, Rollback-Ready

## 1. The Problem

Keprix evolves. Every release brings new features, bug fixes, and optimizations. Products built on Keprix (AbbiS, Petraclus, FleetZ, etc.) need to consume these upgrades safely; with zero risk of breaking existing functionality.

Without an upgrade system, teams either:
- **Never upgrade**: stuck on old Keprix, missing features
- **Upgrade blindly**: breaks in production, emergency rollbacks
- **Manual merge hell**: copy-paste new features, miss edge cases

`keprix upgrade` solves all three.

---

## 2. Core CLI

```bash
# Essential commands
keprix upgrade --check              # Is an upgrade available and safe?
keprix upgrade --dry-run            # Simulate upgrade, run tests
keprix upgrade --to <version>       # Perform the upgrade
keprix upgrade --rollback           # Undo the last upgrade
keprix upgrade --prompt <feature>   # Guided adoption of a new feature
keprix upgrade --list               # Show upgrade history
keprix upgrade --plan               # Show what upgrades are available
```

---

## 3. Upgrade Lifecycle

```
┌─────────────┐
│   --check   │  Read-only. No changes. Answers: "Should I upgrade?"
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  --dry-run  │  Spin up test env. Run product tests against new Keprix.
└──────┬──────┘  Report results. Exit if any test fails.
       │
       ▼
┌─────────────┐
│  --to 0.7.0 │  Full upgrade. Backup → install → migrate → verify → report.
└──────┬──────┘
       │
       ▼  (if anything fails)
┌─────────────┐
│ --rollback   │  Restore from backup. Exactly as before. Zero data loss.
└─────────────┘
```

---

## 4. Step-by-Step Implementation

### 4.1 Upgrade Check (`keprix upgrade --check`)

Read-only. No files changed. Answers one question: *Should I upgrade?*

```python
# keprix/cli/upgrade/check.py

import json
from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass, field
from packaging.version import Version

from keprix.config import KeprixConfig
from keprix.extensions.manifest import ExtensionManifest
from keprix.extensions.loader import ExtensionLoader


@dataclass
class UpgradeCheckResult:
    """Result of `keprix upgrade --check`."""
    product: str
    current_version: Version
    target_version: Version
    available_versions: List[Version]
    compatible: bool
    risk: str                    # "none", "low", "medium", "high", "blocked"
    breaking_changes: List[str]
    deprecated_features: List[str]
    new_features: List[str]
    config_migrations_required: List[str]
    recommendation: str
    changelog_url: str


def check_upgrade(
    manifest: ExtensionManifest,
    config: KeprixConfig,
    target_version: Optional[Version] = None,
) -> UpgradeCheckResult:
    """
    Analyse whether an upgrade is safe.

    Does NOT modify any files.
    """
    current = Version(manifest.keprix.tested_against)
    installed = config.installed_keprix_version

    # What versions are available?
    available = get_available_versions()
    if target_version:
        target = target_version
    else:
        # Default: latest stable
        target = max(v for v in available if not v.is_prerelease)

    # Already on target?
    if installed >= target:
        return UpgradeCheckResult(
            product=manifest.product.name,
            current_version=installed,
            target_version=installed,
            available_versions=available,
            compatible=True,
            risk="none",
            breaking_changes=[],
            deprecated_features=[],
            new_features=[],
            config_migrations_required=[],
            recommendation=f"Already on {installed}. No upgrade needed.",
            changelog_url="",
        )

    # Load changelog for versions between current and target
    changelog = load_changelog(installed, target)

    # Check compatibility
    if target < Version(manifest.keprix.min_version):
        return UpgradeCheckResult(
            product=manifest.product.name,
            current_version=installed,
            target_version=target,
            available_versions=available,
            compatible=False,
            risk="blocked",
            breaking_changes=[],
            deprecated_features=[],
            new_features=[],
            config_migrations_required=[],
            recommendation=(
                f"Cannot upgrade to {target}. "
                f"{manifest.product.name} requires Keprix >= {manifest.keprix.min_version}."
            ),
            changelog_url="",
        )

    # Check known-incompatible versions
    for bad in manifest.keprix.incompatible_with:
        if target == Version(bad):
            return UpgradeCheckResult(
                product=manifest.product.name,
                current_version=installed,
                target_version=target,
                available_versions=available,
                compatible=False,
                risk="blocked",
                breaking_changes=[],
                deprecated_features=[],
                new_features=[],
                config_migrations_required=[],
                recommendation=f"{target} is marked incompatible by {manifest.product.name}. Wait for a fix.",
                changelog_url="",
            )

    # Classify the changelog entries
    breaking = [e for e in changelog if e.get("type") == "breaking"]
    deprecated = [e for e in changelog if e.get("type") == "deprecation"]
    new = [e for e in changelog if e.get("type") == "feature"]
    migrations = [e for e in changelog if e.get("type") == "config_migration"]

    # Compute risk
    if breaking:
        risk = "high"
        rec = f"{len(breaking)} breaking changes. Review carefully before upgrading."
    elif deprecated:
        risk = "medium"
        rec = f"{len(deprecated)} deprecations. Plan migration within 2 releases."
    elif migrations:
        risk = "low"
        rec = f"{len(migrations)} optional config migrations. Safe to upgrade."
    else:
        risk = "none"
        rec = f"Safe to upgrade. {len(new)} new features available."

    return UpgradeCheckResult(
        product=manifest.product.name,
        current_version=installed,
        target_version=target,
        available_versions=available,
        compatible=True,
        risk=risk,
        breaking_changes=breaking,
        deprecated_features=deprecated,
        new_features=new,
        config_migrations_required=migrations,
        recommendation=rec,
        changelog_url=f"https://github.com/malike2356/keprix/releases/tag/v{target}",
    )
```

**CLI output:**

```
$ keprix upgrade --check

 Upgrade Check: AbbiS v1.2.0
   Current Keprix: 0.3.0
   Target Keprix:  0.7.0
   Risk:           LOW (2 optional config migrations)

────────────────────────────────────────────────────────────
Breaking Changes (0)
  None.

Deprecations (1)
  WARNING:   keprix.providers.legacy_api removed in 0.9.0
     → AbbiS does not use this (no action needed)

New Features (7)
   A2A Protocol (0.5.0)     → agent-to-agent communication
   Audit Dashboard (0.5.0)  → web UI for governance
   Semantic Cache (0.6.0)   → free repeated LLM calls
   Spend Tracking (0.6.0)   → per-session cost analytics
   Proxy Pool (0.6.0)       → auto-refreshing free proxies
   Notion Integration (0.6.0) → read/write Notion pages
   CLI Auto-Config (0.7.0)  → detect external tools

Config Migrations (2)
   providers.yaml → providers/providers.yaml (0.5.0)
   audit.db → observability/audit.db (0.5.0)

────────────────────────────────────────────────────────────
Recommendation: Safe to upgrade. 7 new features available.

Next: `keprix upgrade --dry-run --to 0.7.0`
```

---

### 4.2 Dry Run (`keprix upgrade --dry-run`)

Simulates the upgrade in a sandbox. Runs product tests. No permanent changes.

```python
# keprix/cli/upgrade/dry_run.py

import tempfile
import subprocess
import shutil
from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass, field
from packaging.version import Version

from keprix.config import KeprixConfig
from keprix.extensions.manifest import ExtensionManifest


@dataclass
class DryRunResult:
    product: str
    target_version: Version
    passed: bool
    total_tests: int
    passed_tests: int
    failed_tests: int
    warnings: List[str]
    failed_test_details: List[str]
    duration_seconds: float
    recommendation: str


def dry_run_upgrade(
    manifest: ExtensionManifest,
    config: KeprixConfig,
    target_version: Version,
    product_path: Path,
) -> DryRunResult:
    """
    Simulate an upgrade in an isolated environment.

    1. Create temp venv
    2. Install Keprix target version
    3. Install product with test deps
    4. Run pytest
    5. Report results
    6. Clean up
    """
    import time
    start = time.time()

    with tempfile.TemporaryDirectory(prefix="keprix_dryrun_") as sandbox:
        sandbox = Path(sandbox)

        # Clone the product into sandbox
        product_copy = sandbox / manifest.product.slug
        shutil.copytree(product_path, product_copy)

        # Create temp venv
        venv_path = sandbox / "venv"
        subprocess.run(
            ["python3", "-m", "venv", str(venv_path)],
            check=True, capture_output=True,
        )

        pip = venv_path / "bin" / "pip"

        # Install target Keprix version
        result = subprocess.run(
            [str(pip), "install", f"keprix=={target_version}"],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            return DryRunResult(
                product=manifest.product.name,
                target_version=target_version,
                passed=False,
                total_tests=0, passed_tests=0, failed_tests=0,
                warnings=[],
                failed_test_details=[f"Install failed: {result.stderr}"],
                duration_seconds=time.time() - start,
                recommendation=f"Cannot install Keprix {target_version}. Contact Keprix team.",
            )

        # Install product with test deps
        subprocess.run(
            [str(pip), "install", "-e", f"{str(product_copy)}[dev,test]"],
            capture_output=True, text=True, check=True,
        )

        # Run tests
        pytest_bin = venv_path / "bin" / "pytest"
        test_result = subprocess.run(
            [str(pytest_bin), str(product_copy / "tests"), "-v", "--tb=short"],
            capture_output=True, text=True,
        )

        # Parse results
        total, passed, failed = _parse_pytest_output(test_result.stdout)
        warnings = _extract_warnings(test_result.stdout)

        recommendation = (
            "All tests pass. Safe to upgrade."
            if failed == 0
            else f"{failed} test(s) failed. Fix before upgrading."
        )

        return DryRunResult(
            product=manifest.product.name,
            target_version=target_version,
            passed=(failed == 0),
            total_tests=total,
            passed_tests=passed,
            failed_tests=failed,
            warnings=warnings,
            failed_test_details=_extract_failures(test_result.stdout),
            duration_seconds=time.time() - start,
            recommendation=recommendation,
        )
```

**CLI output:**

```
$ keprix upgrade --dry-run --to 0.7.0

 Dry Run: AbbiS v1.2.0 → Keprix 0.7.0

   [1/3] Creating isolated sandbox...
   [2/3] Installing Keprix 0.7.0...
   [3/3] Running 247 tests...

   Done:  PASSED: 247/247
   WARNING:   Warnings: 3 (deprecation)
      · billing.create_invoice() deprecated → use billing.invoice.create()
      · providers.rate_limit_check() → renamed to routing.check_quota()
      · observability.log() → use observability.trace()

   ⏱  Duration: 12.4s

   Recommendation: All tests pass. Safe to upgrade.

   Next: `keprix upgrade --to 0.7.0`
```

**If tests fail:**

```
$ keprix upgrade --dry-run --to 0.7.0

 Dry Run: Petraclus v1.0.0 → Keprix 0.7.0

   [1/3] Creating isolated sandbox...
   [2/3] Installing Keprix 0.7.0...
   [3/3] Running 412 tests...

   Failed:  FAILED: 397/412 (15 failures)

   Failed Tests:
       test_payload_injection; AttributeError: 'PayloadFilter' has no attribute 'max_depth'
       test_nmap_pipeline; AssertionError: expected ScanResult, got dict
      ... (13 more)

   ⏱  Duration: 23.1s

   Recommendation: 15 test(s) failed. Fix before upgrading.
   → See .keprix/upgrade/dry-run-2026-07-02.log for full output.
   → Run `keprix upgrade --plan` to see compatible versions.
```

---

### 4.3 Upgrade Execution (`keprix upgrade --to <version>`)

The real deal. Backup, install, migrate, verify.

```python
# keprix/cli/upgrade/execute.py

import json
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from packaging.version import Version

from keprix.config import KeprixConfig
from keprix.extensions.manifest import ExtensionManifest


class UpgradeExecutor:
    """
    Executes a Keprix upgrade for a product.

    Phases:
      1. PREFLIGHT; validate everything, confirm with user
      2. BACKUP; snapshot current state
      3. INSTALL; pip install new Keprix version
      4. MIGRATE; run config/data migrations
      5. VERIFY; smoke tests
      6. COMMIT; write upgrade record
    """

    def __init__(
        self,
        manifest: ExtensionManifest,
        config: KeprixConfig,
        product_path: Path,
        target_version: Version,
    ):
        self.manifest = manifest
        self.config = config
        self.product_path = product_path
        self.target_version = target_version
        self.upgrade_dir = product_path / ".keprix" / "upgrade"
        self.backup_dir = self.upgrade_dir / "backups" / f"pre-{target_version}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        self.log_file = self.upgrade_dir / f"upgrade-{datetime.now().strftime('%Y%m%d-%H%M%S')}.log"

    def execute(self, skip_confirmation: bool = False) -> bool:
        """Execute the full upgrade. Returns True if successful."""
        self.upgrade_dir.mkdir(parents=True, exist_ok=True)

        # ── Phase 1: PREFLIGHT ───────────────────────────────
        print(" Phase 1/6: Preflight checks...")
        if not self._preflight():
            return False

        if not skip_confirmation:
            confirm = input(f"\nUpgrade {self.manifest.product.name} to Keprix {self.target_version}? [y/N]: ")
            if confirm.lower() != 'y':
                print("Failed:  Upgrade cancelled.")
                return False

        # ── Phase 2: BACKUP ──────────────────────────────────
        print(" Phase 2/6: Creating backup...")
        self._backup()

        # ── Phase 3: INSTALL ─────────────────────────────────
        print(" Phase 3/6: Installing Keprix...")
        if not self._install():
            print("\nFailed:  Install failed. Rolling back...")
            self._rollback()
            return False

        # ── Phase 4: MIGRATE ─────────────────────────────────
        print(" Phase 4/6: Running migrations...")
        if not self._migrate():
            print("\nFailed:  Migration failed. Rolling back...")
            self._rollback()
            return False

        # ── Phase 5: VERIFY ──────────────────────────────────
        print("Done:  Phase 5/6: Verifying...")
        if not self._verify():
            print("\nFailed:  Verification failed. Rolling back...")
            self._rollback()
            return False

        # ── Phase 6: COMMIT ──────────────────────────────────
        print(" Phase 6/6: Recording upgrade...")
        self._commit()

        print(f"\n {self.manifest.product.name} upgraded to Keprix {self.target_version}!")
        return True

    def _preflight(self) -> bool:
        """Validate the upgrade can proceed."""
        # Check disk space (need 500MB free)
        disk_usage = shutil.disk_usage(self.product_path)
        if disk_usage.free < 500 * 1024 * 1024:
            print("Failed:  Insufficient disk space (need 500MB).")
            return False

        # Check no running instances
        if self._is_running():
            print("Failed:  Product is currently running. Stop it first.")
            return False

        # Check git is clean (no uncommitted changes)
        if not self._git_is_clean():
            print("WARNING:   Uncommitted changes detected. Commit or stash first.")
            return False

        # Check lock file (no concurrent upgrades)
        lock_file = self.upgrade_dir / "lock"
        if lock_file.exists():
            print("Failed:  Another upgrade is in progress.")
            return False

        lock_file.touch()
        self._lock_file = lock_file

        return True

    def _backup(self):
        """Snapshot everything that could break."""
        self.backup_dir.mkdir(parents=True)

        # Backup product code
        shutil.copytree(
            self.product_path / self.manifest.product.slug,
            self.backup_dir / self.manifest.product.slug,
            ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '.git'),
        )

        # Backup manifest
        shutil.copy2(
            self.product_path / "keprix.yaml",
            self.backup_dir / "keprix.yaml",
        )

        # Backup config
        config_dir = self.product_path / "config"
        if config_dir.exists():
            shutil.copytree(config_dir, self.backup_dir / "config")

        # Backup billing
        billing = self.product_path / "billing.yaml"
        if billing.exists():
            shutil.copy2(billing, self.backup_dir / "billing.yaml")

        # Save current Keprix version
        (self.backup_dir / "PREVIOUS_KEPRIX_VERSION").write_text(
            str(self.config.installed_keprix_version)
        )

        # Dump pip freeze for reproducibility
        pip_freeze = subprocess.run(
            ["pip", "freeze"], capture_output=True, text=True
        ).stdout
        (self.backup_dir / "pip-freeze.txt").write_text(pip_freeze)

        print(f"   Backup saved: {self.backup_dir}")

    def _install(self) -> bool:
        """Install the target Keprix version."""
        result = subprocess.run(
            ["pip", "install", f"keprix=={self.target_version}"],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            print(f"   pip install failed:\n{result.stderr}")
            return False
        print(f"   {self.target_version} installed successfully.")
        return True

    def _migrate(self) -> bool:
        """Run Keprix's built-in migration for this version jump."""
        from keprix.cli.upgrade.migrations import get_migration_plan, run_migration

        plan = get_migration_plan(
            from_version=self.config.installed_keprix_version,
            to_version=self.target_version,
            manifest=self.manifest,
            product_path=self.product_path,
        )

        if not plan:
            print("   No migrations needed.")
            return True

        for step in plan.steps:
            print(f"   → {step.description}")
            try:
                run_migration(step, self.product_path, self.backup_dir)
                print(f"   Done:  {step.name}")
            except Exception as e:
                print(f"   Failed:  {step.name} failed: {e}")
                return False

        return True

    def _verify(self) -> bool:
        """Run smoke tests to confirm the upgrade works."""
        smoke_tests = [
            self._can_import_keprix,
            self._can_load_manifest,
            self._billing_still_works,
            self._personas_still_load,
        ]

        for test in smoke_tests:
            name = test.__name__.replace('_', ' ').strip()
            try:
                if not test():
                    print(f"   Failed:  {name}")
                    return False
                print(f"   Done:  {name}")
            except Exception as e:
                print(f"   Failed:  {name}: {e}")
                return False

        return True

    def _can_import_keprix(self) -> bool:
        try:
            import keprix
            return True
        except ImportError:
            return False

    def _can_load_manifest(self) -> bool:
        try:
            from keprix.extensions.manifest import ExtensionManifest
            manifest = ExtensionManifest.from_yaml(
                self.product_path / "keprix.yaml"
            )
            return manifest.product.name == self.manifest.product.name
        except Exception:
            return False

    def _billing_still_works(self) -> bool:
        if not self.manifest.features.billing.get("enabled"):
            return True  # Skip if billing not enabled
        try:
            from keprix.billing import load_billing_config
            cfg = load_billing_config(self.product_path / "billing.yaml")
            return cfg is not None
        except Exception:
            return False

    def _personas_still_load(self) -> bool:
        try:
            from keprix.extensions.loader import ExtensionLoader
            from packaging.version import Version
            loader = ExtensionLoader(
                core_version=self.target_version,
                config=self.config,
            )
            ext = loader.load(self.product_path / "keprix.yaml")
            return ext is not None
        except Exception:
            return False

    def _commit(self):
        """Record the upgrade in the history log."""
        history = self.upgrade_dir / "history.json"

        records = []
        if history.exists():
            records = json.loads(history.read_text())

        records.append({
            "from": str(self.config.installed_keprix_version),
            "to": str(self.target_version),
            "timestamp": datetime.now().isoformat(),
            "backup_path": str(self.backup_dir),
            "status": "success",
        })

        history.write_text(json.dumps(records, indent=2))

        # Update tested_against in keprix.yaml
        self._update_manifest_tested_against()

    def _update_manifest_tested_against(self):
        """Update tested_against in keprix.yaml to reflect new version."""
        manifest_path = self.product_path / "keprix.yaml"
        content = manifest_path.read_text()
        content = content.replace(
            f"tested_against: \"{self.manifest.keprix.tested_against}\"",
            f"tested_against: \"{self.target_version}\"",
        )
        manifest_path.write_text(content)

    def _rollback(self):
        """Restore from backup."""
        print("\n Rolling back...")
        # Restore product code
        backup_code = self.backup_dir / self.manifest.product.slug
        if backup_code.exists():
            target_code = self.product_path / self.manifest.product.slug
            if target_code.exists():
                shutil.rmtree(target_code)
            shutil.copytree(backup_code, target_code)

        # Restore manifest
        shutil.copy2(
            self.backup_dir / "keprix.yaml",
            self.product_path / "keprix.yaml",
        )

        # Restore config
        backup_config = self.backup_dir / "config"
        if backup_config.exists():
            target_config = self.product_path / "config"
            if target_config.exists():
                shutil.rmtree(target_config)
            shutil.copytree(backup_config, target_config)

        # Restore billing
        backup_billing = self.backup_dir / "billing.yaml"
        if backup_billing.exists():
            shutil.copy2(backup_billing, self.product_path / "billing.yaml")

        # Reinstall previous Keprix
        prev_version = (self.backup_dir / "PREVIOUS_KEPRIX_VERSION").read_text().strip()
        subprocess.run(
            ["pip", "install", f"keprix=={prev_version}"],
            capture_output=True,
        )

        print(f"Done:  Rolled back to Keprix {prev_version}.")
        print(f"   Backup preserved at: {self.backup_dir}")

    def _is_running(self) -> bool:
        """Check if the product has a running process."""
        import psutil
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            cmdline = proc.info.get('cmdline') or []
            if self.manifest.product.slug in ' '.join(cmdline):
                return True
        return False

    def _git_is_clean(self) -> bool:
        """Check if git working directory is clean."""
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True, text=True,
            cwd=self.product_path,
        )
        return result.stdout.strip() == ""
```

**CLI output:**

```
$ keprix upgrade --to 0.7.0

 Phase 1/6: Preflight checks...
   Done:  Disk space: 12.3 GB free
   Done:  No running instances
   Done:  Git working directory clean

 Phase 2/6: Creating backup...
   Backup saved: .keprix/upgrade/backups/pre-0.7.0-20260702T143022/

 Phase 3/6: Installing Keprix...
   Done:  Keprix 0.7.0 installed

 Phase 4/6: Running migrations...
   → Move providers.yaml to providers/providers.yaml
   Done:  config-layout-v2
   → Move audit.db to observability/audit.db
   Done:  audit-relocation
   → Add new routing section to keprix.yaml
   Done:  routing-config-v1

Done:  Phase 5/6: Verifying...
   Done:  can import keprix
   Done:  can load manifest
   Done:  billing still works
   Done:  personas still load

 Phase 6/6: Recording upgrade...
   Done:  History updated

 AbbiS upgraded to Keprix 0.7.0!

   Changes applied:
       7 new features available (opt-in via keprix.yaml)
      WARNING:   1 deprecation (fix before Keprix 0.9.0)
       2 config migrations applied

   Next: Review new features with `keprix upgrade --plan`
```

---

### 4.4 Rollback (`keprix upgrade --rollback`)

```bash
$ keprix upgrade --rollback

 Rollback

   Reverting AbbiS from Keprix 0.7.0 → 0.3.0

   [1/3] Restoring code from backup...
   [2/3] Restoring config from backup...
   [3/3] Reinstalling Keprix 0.3.0...

   Done:  Rolled back to Keprix 0.3.0.
   ⏱  Duration: 4.7 seconds.
    Backup preserved: .keprix/upgrade/backups/pre-0.7.0-20260702T143022/

   Note: Any data created while running 0.7.0 was NOT affected.
   Only code and config were restored.
```

---

### 4.5 Guided Feature Adoption (`keprix upgrade --prompt <feature>`)

New features in a Keprix upgrade are *available* but not *activated*. Products opt in:

```bash
$ keprix upgrade --prompt adopt-a2a

 Feature Adoption: A2A Protocol (Agent-to-Agent)

   This feature enables AbbiS to communicate with other Keprix agents.
   It was added in Keprix 0.5.0 and is currently disabled.

   What it does:
   · AbbiS can delegate tasks to other AI agents
   · Receives results from federated agents
   · Supports streaming and batch modes

   What it needs:
; keprix.yaml: features.a2a.enabled = true
; config/a2a.yaml: agent registry, trust policy
; Optional: mutual TLS certs for secure channels

   Risks:
   · Network exposure (agents communicate over HTTP/gRPC)
   · Additional latency per delegation (~200-500ms)
   · Requires agent discovery service running

   Apply this feature? [y/N]: y

   Done:  keprix.yaml updated (a2a: enabled)
   Done:  config/a2a.yaml created with defaults
   Done:  Smoke test: A2A endpoint responds

   AbbiS now has A2A capabilities.

   To test: `abbis agent list` or `abbis agent ping scout`
```

**Other guided prompts:**

| Prompt | What it helps adopt |
|--------|-------------------|
| `adopt-billing` | Stripe subscriptions, plans, webhooks |
| `adopt-governance` | SCOUT personas, audit rules |
| `adopt-routing` | Combo routing, provider fallback |
| `adopt-compression` | RTK + Caveman token compression |
| `adopt-guardrails` | PII masking, prompt injection |
| `adopt-a2a` | Agent-to-agent protocol |
| `adopt-observability` | Audit dashboard, traces, metrics |
| `adopt-cache` | Semantic prompt cache |
| `adopt-spend` | Cost tracking per session/agent |
| `adopt-proxy` | Free proxy pool |
| `adopt-notion` | Notion page read/write MCP tools |
| `adopt-cli` | External tool auto-detection |

---

### 4.6 Upgrade History (`keprix upgrade --list`)

```bash
$ keprix upgrade --list

   AbbiS Upgrade History
   ─────────────────────────────────────────────────────────────
   #  From     To       Date               Status    Duration
   ─────────────────────────────────────────────────────────────
   1  0.1.0    0.2.0    2026-01-15 09:22   Done:  pass    8.2s
   2  0.2.0    0.3.0    2026-03-03 14:11   Done:  pass    11.4s
   3  0.3.0    0.5.0    2026-05-20 10:45   Done:  pass    15.3s
   4  0.5.0    0.7.0    2026-07-02 14:30   Done:  pass    9.1s
   ─────────────────────────────────────────────────────────────
   Current: 0.7.0  |  Available: 0.7.1 (patch)

   All backups preserved in .keprix/upgrade/backups/
```

---

### 4.7 Upgrade Plan (`keprix upgrade --plan`)

Shows the upgrade path and what you get at each step:

```bash
$ keprix upgrade --plan

   Upgrade Path: AbbiS on Keprix 0.3.0 → 0.7.0

   Step 1: 0.3.0 → 0.4.0
       Compression (RTK + Caveman)
       Guardrails (PII, injection)
      Risk: LOW
      0 breaking changes

   Step 2: 0.4.0 → 0.5.0
       A2A Protocol
       Observability (audit, traces)
       2 config migrations
      Risk: LOW

   Step 3: 0.5.0 → 0.6.0
       Operational Excellence (cache, spend, proxy)
       Notion Integration
      Risk: LOW

   Step 4: 0.6.0 → 0.7.0
       CLI Auto-Config
       Provider Catalog Sync
      Risk: LOW

   Direct jump: 0.3.0 → 0.7.0 (recommended)
      All intermediate migrations are cumulative.
```

---

## 5. Migration Framework

Keprix ships migrations that run automatically during upgrade:

```python
# keprix/cli/upgrade/migrations.py

from dataclasses import dataclass
from typing import List, Callable, Optional
from pathlib import Path
from packaging.version import Version
import yaml


@dataclass
class MigrationStep:
    name: str
    from_version: Version
    description: str
    reversible: bool
    execute: Callable
    rollback: Optional[Callable] = None


# Registry of all known migrations
MIGRATIONS: List[MigrationStep] = []


def register_migration(step: MigrationStep):
    """Decorator-free registration (called at module init)."""
    MIGRATIONS.append(step)


# ── Example migrations ──────────────────────────────────

def migrate_config_layout_v2(product_path: Path, backup_dir: Path):
    """Move providers.yaml to providers/ subdirectory."""
    old = product_path / "config" / "providers.yaml"
    new_dir = product_path / "config" / "providers"
    if old.exists() and not new_dir.exists():
        new_dir.mkdir(parents=True)
        old.rename(new_dir / "providers.yaml")

def rollback_config_layout_v2(product_path: Path, backup_dir: Path):
    """Reverse the config layout migration."""
    new = product_path / "config" / "providers" / "providers.yaml"
    old = product_path / "config" / "providers.yaml"
    if new.exists():
        product_path / "config" / "providers"
        new.rename(old)
        new.parent.rmdir()


register_migration(MigrationStep(
    name="config-layout-v2",
    from_version=Version("0.5.0"),
    description="Move providers.yaml to providers/providers.yaml",
    reversible=True,
    execute=migrate_config_layout_v2,
    rollback=rollback_config_layout_v2,
))


def migrate_add_routing_section(product_path: Path, backup_dir: Path):
    """Add routing section to keprix.yaml if missing."""
    manifest_path = product_path / "keprix.yaml"
    manifest = yaml.safe_load(manifest_path.read_text())

    if "routing" not in manifest.get("features", {}):
        manifest.setdefault("features", {})["routing"] = {
            "enabled": False,
            "combos": False,
            "circuit_breaker": True,
        }
        manifest_path.write_text(yaml.dump(manifest, default_flow_style=False))


register_migration(MigrationStep(
    name="routing-config-v1",
    from_version=Version("0.5.0"),
    description="Add routing section to keprix.yaml",
    reversible=True,
    execute=migrate_add_routing_section,
    rollback=None,  # Harmless to leave the section
))


def get_migration_plan(
    from_version: Version,
    to_version: Version,
    manifest,
    product_path: Path,
) -> Optional["MigrationPlan"]:
    """Return ordered list of migrations between two versions."""
    applicable = [
        m for m in MIGRATIONS
        if from_version < m.from_version <= to_version
    ]
    if not applicable:
        return None  # No migrations needed

    return MigrationPlan(steps=sorted(applicable, key=lambda m: m.from_version))


@dataclass
class MigrationPlan:
    steps: List[MigrationStep]
```

---

## 6. Changelog Format

Keprix's changelog drives the `--check` output. Standard format in `CHANGELOG.yaml`:

```yaml
# keprix/CHANGELOG.yaml
- version: "0.7.0"
  date: "2026-07-01"
  entries:
    - type: feature
      id: "cli-auto-config"
      title: "CLI Tool Auto-Config"
      description: "Auto-detect and configure Claude Code, Codex, Cursor, etc."
      requires_config: false
      requires_migration: false
      product_impact: "none"

    - type: feature
      id: "model-catalog-sync"
      title: "Provider Model Catalog Sync"
      description: "Keep provider model catalogs current automatically."
      requires_config: true
      requires_migration: false
      product_impact: "none"

    - type: deprecation
      id: "depr-billing-v1"
      title: "billing.create_invoice() deprecated"
      description: "Use billing.invoice.create() instead."
      deprecated_since: "0.6.0"
      removal_version: "0.9.0"
      product_impact: "low"

    - type: fix
      id: "fix-provider-timeout"
      title: "Fix provider timeout on slow connections"
      description: "Default timeout increased from 30s to 120s."
```

---

## 7. Full CLI Reference

```bash
keprix upgrade
    --check                        Check upgrade availability and risk
    --dry-run                      Simulate upgrade in sandbox, run tests
    --to <version>                 Execute upgrade to specific version
    --to latest                    Upgrade to latest stable
    --to latest --include-pre      Include pre-release versions
    --rollback                     Undo last upgrade
    --prompt adopt-<feature>       Guided feature adoption wizard
    --prompt migrate-<id>          Run a specific migration
    --list                         Show upgrade history
    --plan                         Show available upgrade path
    --plan --step                  Show step-by-step path with details
    --skip-tests                   Skip dry-run test suite (dangerous)
    --force                        Skip all confirmations
    --backup-path <path>           Custom backup location
    --log-level debug              Verbose logging

keprix extension <product>
    features available             List available features not yet enabled
    features enable <name>         Enable a feature with guided setup
    features disable <name>        Disable a feature (if optional)
    version                        Show current Keprix version for this product
    compat                         Check version compatibility
    deps                           Show Keprix dependency tree
```

---

## 8. Safety Guarantees

| Scenario | Behaviour |
|----------|-----------|
| **Insufficient disk** | Blocked; "need 500MB free" |
| **Product running** | Blocked; "stop the process first" |
| **Uncommitted git changes** | Blocked; "commit or stash" |
| **Concurrent upgrade** | Blocked; "another upgrade in progress" |
| **Incompatible version** | Blocked; "Keprix 0.8.0 is incompatible with AbbiS" |
| **Install fails** | Auto-rollback from backup |
| **Migration fails** | Auto-rollback from backup |
| **Verification fails** | Auto-rollback from backup |
| **Tests fail (dry run)** | Blocked; "fix the 3 failing tests" |
| **Power loss mid-upgrade** | Backup untouched, re-run on restart |
| **Data created during upgrade** | Preserved (only code/config rolled back) |

---

## 9. Integration with CI/CD

```yaml
# .github/workflows/keprix-upgrade-check.yml
name: Keprix Compatibility Check

on:
  schedule:
    - cron: "0 6 * * 1"          # Every Monday at 6am
  workflow_dispatch:

jobs:
  check:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        product: [abbis, petraclus, fleet-z]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Install product
        run: pip install -e ".[dev,test]"
      - name: Check for Keprix updates
        run: |
          keprix upgrade --check --json > upgrade-check.json
          cat upgrade-check.json
      - name: Dry-run upgrade
        if: ${{ fromJson(steps.check.outputs.result).compatible }}
        run: keprix upgrade --dry-run --to latest
      - name: Notify on breaking changes
        if: ${{ fromJson(steps.check.outputs.result).risk == 'high' }}
        uses: slackapi/slack-github-action@v1
        with:
          payload: |
            {
              "text": "WARNING:  Keprix upgrade has breaking changes for ${{ matrix.product }}. See upgrade-check.json."
            }
```

---

## 10. Summary

| Concern | How `keprix upgrade` Handles It |
|---------|-------------------------------|
| "Will it break my product?" | `--check` analyses changelog for breaking changes |
| "Will my tests pass?" | `--dry-run` runs full test suite in sandbox |
| "Can I go back?" | `--rollback` restores from backup in seconds |
| "What's new?" | `--plan` shows feature roadmap per version |
| "How do I adopt a feature?" | `--prompt adopt-<feature>` guided wizard |
| "What did I upgrade?" | `--list` shows full history with timestamps |
| "Is it safe to skip versions?" | Migrations are cumulative; jump any number of versions |
| "What if power fails?" | Backup is a complete filesystem snapshot, untouched |
| "Can CI/CD check automatically?" | GitHub Action included, runs weekly |

**Upgrades become boring. That's the point.**
