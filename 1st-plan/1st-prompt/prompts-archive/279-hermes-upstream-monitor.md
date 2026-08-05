# Prompt 89; Keprix Hermes Upstream Monitor & Feature Adoption Pipeline

## 0. Strategic Context

Hermes Agent (original) is evolving fast. Julien Goldie's 408k-subscriber channel is driving adoption. Every Hermes release adds features; and every feature adds attack surface. Keprix's job: adopt the features, harden them with security, and ship them as Scout-integrated.

This prompt builds the system that keeps Keprix current with Hermes upstream while maintaining the security edge Hermes lacks.

## 1. The Monitor

### 1.1 What To Track

```python
# keprix/upstream/hermes_monitor.py

"""
Monitors Hermes Agent upstream for new releases, features, and changes.

Tracked sources:
- GitHub releases: https://github.com/NousResearch/hermes-agent/releases
- PyPI: https://pypi.org/project/hermes-agent/
- Changelog: CHANGELOG.md in the repo
- Julian Goldie videos: new features he demonstrates (community signal)
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional
from packaging.version import Version

import httpx
import yaml


class FeatureCategory(Enum):
    TOOL = "tool"                   # New MCP tool
    PROVIDER = "provider"           # New model provider
    ROUTING = "routing"             # Smart routing, combos
    MEMORY = "memory"               # Workspace, session memory
    COMPRESSION = "compression"     # Token compression
    UI_CLI = "ui_cli"              # CLI, TUI, dashboard
    PLATFORM = "platform"           # Multi-platform, Android, desktop
    SECURITY = "security"           # Security features (rare in Hermes)
    INTEGRATION = "integration"     # Third-party integrations
    PERFORMANCE = "performance"     # Speed, caching, optimisation
    OTHER = "other"


class AdoptionStatus(Enum):
    UNEVALUATED = "unevaluated"       # Not yet assessed
    ALREADY_HAVE = "already_have"     # Keprix already has this
    ADOPT = "adopt"                   # Should adopt; write prompt
    ADOPT_WITH_HARDENING = "adopt_with_hardening"  # Adopt + add security layer
    SKIP = "skip"                     # Not relevant to Keprix
    DEFER = "defer"                   # Revisit later
    BLOCKED = "blocked"               # Conflicts with Keprix architecture


@dataclass
class UpstreamFeature:
    """A feature from an upstream Hermes release."""
    feature_id: str
    name: str
    description: str
    category: FeatureCategory
    version_introduced: Version
    release_date: datetime
    release_url: str
    adoption_status: AdoptionStatus = AdoptionStatus.UNEVALUATED
    adoption_prompt_id: Optional[str] = None  # Keprix prompt number
    security_implications: List[str] = field(default_factory=list)
    keprix_equivalent: Optional[str] = None   # What Keprix already has
    notes: str = ""


class HermesMonitor:
    """
    Monitors Hermes Agent upstream releases and tracks feature adoption.

    Runs as a cron job (daily). Checks GitHub releases + PyPI.
    Compares against Keprix's feature inventory.
    Generates adoption recommendations.
    """

    GITHUB_API = "https://api.github.com/repos/NousResearch/hermes-agent/releases"
    PYPI_API = "https://pypi.org/pypi/hermes-agent/json"
    CHECK_INTERVAL_HOURS = 24

    def __init__(self, inventory_path: str):
        self.inventory_path = inventory_path
        self.inventory: dict = self._load_inventory()
        self.keprix_version = self._get_keprix_version()

    async def check(self) -> List[UpstreamFeature]:
        """Check for new Hermes releases. Return features Keprix should adopt."""
        releases = await self._fetch_releases()
        new_features = []

        for release in releases:
            version = Version(release["tag_name"].lstrip("v"))

            # Skip versions we've already processed
            if str(version) in self.inventory.get("processed_versions", []):
                continue

            # Parse features from release notes
            features = self._parse_release_notes(release)

            for feature in features:
                # Check if Keprix already has this
                feature.adoption_status = self._evaluate_adoption(feature)
                feature.security_implications = self._assess_security(feature)
                new_features.append(feature)

            # Mark version as processed
            self.inventory.setdefault("processed_versions", []).append(str(version))

        self._save_inventory()
        return new_features

    async def _fetch_releases(self) -> list:
        """Fetch releases from GitHub + PyPI."""
        releases = []

        # GitHub
        async with httpx.AsyncClient() as client:
            resp = await client.get(self.GITHUB_API, timeout=15)
            if resp.status_code == 200:
                releases.extend(resp.json())

        return releases

    def _parse_release_notes(self, release: dict) -> List[UpstreamFeature]:
        """Extract features from release notes body."""
        body = release.get("body", "")
        version = Version(release["tag_name"].lstrip("v"))
        release_date = datetime.fromisoformat(release["published_at"].rstrip("Z"))
        features = []

        # Parse markdown sections
        # Look for: ## New Features, ## Changes, ## Added
        # Each bullet point is a potential feature

        sections = body.split("## ")
        for section in sections:
            if not section.strip():
                continue

            lines = section.split("\n")
            section_title = lines[0].strip().lower()

            for line in lines[1:]:
                line = line.strip()
                if line.startswith("- ") or line.startswith("* "):
                    feature_text = line[2:].strip()
                    if len(feature_text) > 10:  # Skip trivial entries
                        cat = self._categorise(feature_text, section_title)
                        feature = UpstreamFeature(
                            feature_id=f"hermes-{version}-{hash(feature_text) % 10000:04d}",
                            name=feature_text[:100],
                            description=feature_text,
                            category=cat,
                            version_introduced=version,
                            release_date=release_date,
                            release_url=release["html_url"],
                        )
                        features.append(feature)

        return features

    def _categorise(self, text: str, section: str) -> FeatureCategory:
        """Categorise a feature based on its description."""
        text_lower = text.lower()

        if any(w in text_lower for w in ["tool", "mcp", "execute", "browser"]):
            return FeatureCategory.TOOL
        if any(w in text_lower for w in ["provider", "model", "openai", "anthropic", "api"]):
            return FeatureCategory.PROVIDER
        if any(w in text_lower for w in ["routing", "fallback", "combo", "quota"]):
            return FeatureCategory.ROUTING
        if any(w in text_lower for w in ["memory", "workspace", "session", "persist"]):
            return FeatureCategory.MEMORY
        if any(w in text_lower for w in ["compress", "token", "context"]):
            return FeatureCategory.COMPRESSION
        if any(w in text_lower for w in ["cli", "tui", "dashboard", "ui"]):
            return FeatureCategory.UI_CLI
        if any(w in text_lower for w in ["android", "ios", "mobile", "desktop", "platform"]):
            return FeatureCategory.PLATFORM
        if any(w in text_lower for w in ["security", "sandbox", "auth", "encrypt"]):
            return FeatureCategory.SECURITY
        if any(w in text_lower for w in ["integration", "webhook", "api", "plugin"]):
            return FeatureCategory.INTEGRATION
        if any(w in text_lower for w in ["performance", "speed", "cache", "faster"]):
            return FeatureCategory.PERFORMANCE

        return FeatureCategory.OTHER

    def _evaluate_adoption(self, feature: UpstreamFeature) -> AdoptionStatus:
        """Determine whether and how Keprix should adopt this feature."""

        # Check if Keprix already has an equivalent
        for existing_id, existing_desc in self.inventory.get("keprix_features", {}).items():
            if self._is_equivalent(feature, existing_desc):
                feature.keprix_equivalent = existing_id
                return AdoptionStatus.ALREADY_HAVE

        # Features Keprix should always adopt
        ALWAYS_ADOPT = [
            FeatureCategory.TOOL,
            FeatureCategory.PROVIDER,
            FeatureCategory.ROUTING,
            FeatureCategory.COMPRESSION,
        ]
        if feature.category in ALWAYS_ADOPT:
            return AdoptionStatus.ADOPT_WITH_HARDENING

        # Features to evaluate case-by-case
        EVALUATE = [
            FeatureCategory.MEMORY,
            FeatureCategory.INTEGRATION,
            FeatureCategory.PERFORMANCE,
            FeatureCategory.UI_CLI,
        ]
        if feature.category in EVALUATE:
            return AdoptionStatus.UNEVALUATED  # Needs human review

        # Features to skip (platform-specific, not relevant)
        SKIP = [
            FeatureCategory.PLATFORM,  # Keprix has its own Android app
        ]
        if feature.category in SKIP:
            return AdoptionStatus.SKIP

        return AdoptionStatus.UNEVALUATED

    def _assess_security(self, feature: UpstreamFeature) -> List[str]:
        """Assess security implications of adopting this feature."""
        implications = []

        if feature.category == FeatureCategory.TOOL:
            implications.append("New tool = new attack surface. Must pass through sandbox + governance.")
            implications.append("Add to tool policy: allowlist/blocklist, rate limits, confirmation rules.")
            implications.append("Emit Scout signals for tool invocation.")

        if feature.category == FeatureCategory.PROVIDER:
            implications.append("New provider = new API key. Must go into credential vault, not env/config.")
            implications.append("Provider must be added to egress filter domain allowlist.")
            implications.append("Test for SSRF; provider endpoints can be spoofed.")

        if feature.category == FeatureCategory.MEMORY:
            implications.append("Memory is a persistence vector. Scan writes with MEM-001 through MEM-007.")
            implications.append("Memory content scanner must run before every write.")
            implications.append("Memory content can be poisoned across sessions; threat pattern scan required.")

        if feature.category == FeatureCategory.INTEGRATION:
            implications.append("Third-party integration = supply chain risk.")
            implications.append("Skills guard must scan integration code before loading.")
            implications.append("Add integration domains to egress filter allowlist.")

        if feature.category == FeatureCategory.COMPRESSION:
            implications.append("Compression can hide injection payloads. Decompress before scanning.")
            implications.append("Input sanitizer must run on decompressed content, not compressed.")

        return implications

    def _is_equivalent(self, feature: UpstreamFeature, existing_desc: str) -> bool:
        """Check if Keprix already has an equivalent feature."""
        # Simple keyword overlap check
        feature_words = set(feature.description.lower().split())
        existing_words = set(existing_desc.lower().split())
        overlap = feature_words & existing_words
        return len(overlap) / max(len(feature_words), 1) > 0.5

    def _load_inventory(self) -> dict:
        """Load the feature inventory YAML."""
        import os
        if os.path.exists(self.inventory_path):
            with open(self.inventory_path) as f:
                return yaml.safe_load(f) or {}
        return {"processed_versions": [], "keprix_features": {}}

    def _save_inventory(self):
        """Save the feature inventory YAML."""
        with open(self.inventory_path, 'w') as f:
            yaml.dump(self.inventory, f, default_flow_style=False)

    def _get_keprix_version(self) -> Version:
        """Get current Keprix version."""
        try:
            from keprix import __version__
            return Version(__version__)
        except ImportError:
            return Version("0.1.0")
```

### 1.2 Feature Inventory File

```yaml
# keprix/upstream/hermes_inventory.yaml

processed_versions:
  - "0.17.0"

keprix_features:
  prompt-77: "De-brand; remove hardcoded product names"
  prompt-78: "SaaS billing; pluggable Stripe subscriptions"
  prompt-79: "Smart routing; combos, quota, auto-fallback"
  prompt-80: "Compression; RTK + Caveman, PII masking, injection defense"
  prompt-81: "A2A; agent-to-agent protocol, compliance, observability"
  prompt-82: "Operations; prompt cache, spend tracker, format translator, headroom, credentials, proxy, CLI config, model sync"
  prompt-83: "Notion integration; MCP tools, context loader, exporter"
  prompt-84: "Extension architecture; products as plugins, not forks"
  prompt-85: "Upgrade system; safe CLI, dry-run, backup, rollback"
  prompt-86: "Upgrade alerts; notifications, GUI wizard, scheduler"
  prompt-87: "Security architecture; 7-layer defense-in-depth"
  prompt-88: "Scout integration; ScoutClient, ScoutListener, ScoutSync"
  prompt-89: "Upstream monitor; this prompt"

last_check: null
next_prompt_number: 90
```

---

## 2. The Adoption Pipeline

When the monitor finds a feature Keprix should adopt:

```
Hermes releases v0.18.0 with "New browser automation tool"
  ↓
Monitor detects → category: TOOL → status: ADOPT_WITH_HARDENING
  ↓
Pipeline generates adoption prompt (numbered sequentially)
  ↓
Prompt structure:
  1. What Hermes added
  2. What Keprix builds (equivalent + security hardening)
  3. Scout signals to emit
  4. Governance rules to add
  5. Tests (functional + security)
  ↓
Implementation → PR → merge → inventory updated → prompt archived
```

### 2.1 Adoption Prompt Template

```markdown
# Prompt {N}; Adopt Hermes Feature: {feature_name}

## Upstream Source
- **Hermes version:** {version}
- **Release date:** {date}
- **Release URL:** {url}
- **Category:** {category}

## What Hermes Added
{description from release notes}

## Security Assessment
{security_implications; one per line}

## What Keprix Builds

### 1. Feature Implementation
{How to implement equivalent in Keprix}

### 2. Security Hardening
{Additional security layers beyond what Hermes has}

### 3. Scout Integration
- Signal types to emit
- Governance rules to add
- ScoutListener commands to handle (if any)

### 4. Tests
- Functional tests
- Security tests (injection, sandbox escape, credential leak)
- Scout integration tests

## Files to Create/Modify
- `keprix/{path}/`; description
- `tests/{path}/`; description

## Acceptance Criteria
- [ ] Feature works as described
- [ ] Passes all security tests
- [ ] Scout signals emitted correctly
- [ ] Governance rules triggered appropriately
- [ ] No regression in existing tests
```

---

## 3. The Cron Job

```bash
# Daily check for Hermes upstream updates
# Runs at 6 AM UTC; before the workday starts

keprix upstream check
```

```python
# keprix/cli/upstream.py

"""
CLI for upstream monitoring and adoption.

Commands:
  keprix upstream check          Check for new Hermes releases
  keprix upstream list           List tracked features and adoption status
  keprix upstream adopt <id>     Generate adoption prompt for a feature
  keprix upstream diff           Show diff between Keprix and Hermes feature sets
  keprix upstream report         Generate weekly adoption report
"""

import asyncio
import click
from datetime import datetime

from keprix.upstream.hermes_monitor import HermesMonitor, AdoptionStatus


@click.group()
def upstream():
    """Monitor and adopt features from upstream Hermes Agent."""
    pass


@upstream.command()
@click.option("--json", "json_output", is_flag=True, help="Output as JSON")
def check(json_output):
    """Check for new Hermes releases. Show features to adopt."""
    monitor = HermesMonitor("keprix/upstream/hermes_inventory.yaml")
    features = asyncio.run(monitor.check())

    if not features:
        click.echo("Done:  Keprix is current. No new Hermes features to adopt.")
        return

    click.echo(f"\n Found {len(features)} new feature(s) from Hermes upstream:\n")

    for f in features:
        status_icon = {
            AdoptionStatus.ALREADY_HAVE: "Done: ",
            AdoptionStatus.ADOPT: "",
            AdoptionStatus.ADOPT_WITH_HARDENING: "",
            AdoptionStatus.SKIP: "⏭",
            AdoptionStatus.UNEVALUATED: "",
        }.get(f.adoption_status, "")

        click.echo(f"  {status_icon} [{f.category.value}] {f.name}")
        click.echo(f"     Status: {f.adoption_status.value}")
        click.echo(f"     Version: {f.version_introduced}")
        click.echo(f"     Security: {', '.join(f.security_implications) if f.security_implications else 'none'}")
        click.echo()

    click.echo(f"Run 'keprix upstream adopt <id>' to generate adoption prompts.")


@upstream.command()
@click.option("--category", "-c", help="Filter by category")
@click.option("--status", "-s", help="Filter by adoption status")
def list(category, status):
    """List all tracked upstream features and adoption status."""
    monitor = HermesMonitor("keprix/upstream/hermes_inventory.yaml")
    # Load and display inventory
    click.echo("Feature inventory loaded.")


@upstream.command()
@click.argument("feature_id")
def adopt(feature_id):
    """Generate an adoption prompt for a specific upstream feature."""
    click.echo(f"Generating adoption prompt for {feature_id}...")
    # Template-based prompt generation
    # Creates: planning/prompts/{next_number}-adopt-hermes-{slug}.md


@upstream.command()
def report():
    """Generate weekly upstream adoption report."""
    from keprix.upstream.hermes_monitor import HermesMonitor
    monitor = HermesMonitor("keprix/upstream/hermes_inventory.yaml")

    click.echo("=" * 60)
    click.echo("KEPRIX UPSTREAM ADOPTION REPORT")
    click.echo(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    click.echo("=" * 60)

    # Stats
    inventory = monitor.inventory
    total_features = len(inventory.get("keprix_features", {}))
    processed = len(inventory.get("processed_versions", []))
    next_prompt = inventory.get("next_prompt_number", 90)

    click.echo(f"\n  Hermes versions tracked: {processed}")
    click.echo(f"  Keprix prompts: {next_prompt - 77} (77-{next_prompt - 1})")
    click.echo(f"  Next prompt number: {next_prompt}")
    click.echo(f"  Last check: {inventory.get('last_check', 'never')}")

    # Adoption summary by category would go here
```

---

## 4. Integration with Existing Systems

### 4.1 Cron Job Registration

```bash
# Deploy as a cron job
hermes cron create \
  --name "keprix-upstream-check" \
  --schedule "0 6 * * *" \
  --prompt "Run 'keprix upstream check' and report any new Hermes features that should be adopted into Keprix. For each feature, assess security implications and recommend adoption priority." \
  --deliver telegram:7028923891 \
  --enabled-toolsets terminal,file
```

### 4.2 Scout Integration

When upstream features are adopted, Scout gets visibility:

| Event | Scout Signal |
|-------|-------------|
| New Hermes release detected | `upstream.new_release` with version, feature count |
| Feature adopted into Keprix | `upstream.feature_adopted` with prompt ID, security assessment |
| Feature adoption deferred | `upstream.feature_deferred` with reason |
| Security gap detected | `upstream.security_gap`; feature adopted without hardening |

### 4.3 Dashboard

```
┌──────────────────────────────────────────────────────────────┐
│  Keprix Upstream Monitor                                     │
│                                                              │
│  Hermes v0.17.0    Keprix v0.7.0    Gap: 0 new features     │
│  ─────────────────────────────────────────────────────────── │
│                                                              │
│  Feature Adoption Pipeline                                   │
│  ┌──────────────────────────────────────────────────────┐    │
│  │ Done:  Web Search        → Adopted (Prompt 82)            │    │
│  │ Done:  Web Extract       → Adopted (Prompt 82)            │    │
│  │ Done:  Workspace Memory  → Adopted + scanned (Prompt 82)  │    │
│  │  Browser Tool      → Pending (security review)      │    │
│  │ ⏭ Desktop App       → Skipped (Keprix has own)       │    │
│  └──────────────────────────────────────────────────────┘    │
│                                                              │
│  Last check: 2026-07-09 06:00 UTC  |  Next: 2026-07-10      │
│  [Check Now]  [Generate Report]                              │
└──────────────────────────────────────────────────────────────┘
```

---

## 5. The Security Advantage

Every Hermes feature Keprix adopts gets these security layers that Hermes lacks:

| Hermes Ships | Keprix Adds |
|---|---|
| New tool | → Sandbox policy, governance rules, Scout signals |
| New provider | → Credential vault, egress filter allowlist |
| New memory feature | → MEM-001 through MEM-007 content scanner |
| New integration | → Skills guard scan, domain allowlist |
| New compression | → Decompress-before-scan pipeline |
| Any feature | → Prompt injection defense, audit trail, Scout kill switch |

**The result:** Keprix adopts everything Hermes builds, but ships it with military-grade security. Every feature is a Scout-attested, Scout-protected, Scout-monitored capability.

---

## 6. Implementation Checklist

| # | File | Purpose |
|---|------|---------|
| 1 | `keprix/upstream/__init__.py` | Package init |
| 2 | `keprix/upstream/hermes_monitor.py` | Release monitoring, feature extraction, adoption evaluation |
| 3 | `keprix/upstream/hermes_inventory.yaml` | Feature inventory + adoption state |
| 4 | `keprix/upstream/hermes_adoption.py` | Adoption prompt generator |
| 5 | `keprix/cli/upstream.py` | CLI commands: check, list, adopt, diff, report |
| 6 | `keprix/upstream/templates/adoption_prompt.md` | Template for adoption prompts |
| 7 | `tests/upstream/test_hermes_monitor.py` | Monitor tests |
| 8 | `tests/upstream/test_adoption.py` | Adoption pipeline tests |
| 9 | Cron job registration | Daily upstream check |
| 10 | Scout signal integration | `upstream.new_release`, `upstream.feature_adopted` |

---

## 7. Summary

**Keprix doesn't compete with Hermes on features. Keprix competes on security.**

The upstream monitor ensures Keprix never falls behind on features. The adoption pipeline ensures every feature is hardened before it reaches production. Scout ensures every feature is monitored and controllable.

```
Hermes ships → Monitor detects → Keprix adopts + hardens + Scout-integrates

Result: Keprix always has Hermes' features.
         Hermes never has Keprix' security.
```
