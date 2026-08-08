# Prompt 92; Multi-Product Scout Dashboard & Per-Product Security Policies

## 0. What This Completes

Keprix runs multiple products (AbbiS, Petraclus, FleetZ). Each has different security needs. Scout must distinguish between them, apply per-product policies, and present a unified dashboard.

## 1. Product Registration in Scout

When a Keprix product boots, it registers with Scout:

```python
# keprix/security/scout_registration.py

@dataclass
class ProductRegistration:
    product_id: str           # "abbis", "petraclus", "fleet_z"
    product_name: str         # "AbbiS", "Petraclus", "FleetZ"
    product_version: str      # "1.2.0"
    keprix_version: str       # "0.7.0"
    instance_id: str          # Unique per deployment
    features: dict            # Enabled feature gates from keprix.yaml
    security_profile: str     # "standard", "high", "maximum"
    registered_at: str
    last_heartbeat: str


class ScoutRegistration:
    """Registers a Keprix product instance with Scout on startup."""

    SCOUT_REGISTER_ENDPOINT = "https://console.labyrinthscout.com/api/v1/agents/register"

    async def register(self, manifest, config) -> ProductRegistration:
        """Register this product with Scout. Called once at boot."""
        registration = ProductRegistration(
            product_id=manifest.product.slug,
            product_name=manifest.product.name,
            product_version=manifest.product.version,
            keprix_version=config.keprix_version,
            instance_id=config.instance_id,
            features=manifest.features,
            security_profile=self._determine_profile(manifest),
            registered_at=datetime.now(timezone.utc).isoformat(),
            last_heartbeat=datetime.now(timezone.utc).isoformat(),
        )

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                self.SCOUT_REGISTER_ENDPOINT,
                json=asdict(registration),
                headers={"Authorization": f"Bearer {config.scout_api_key}"},
            )
            resp.raise_for_status()

        return registration

    def _determine_profile(self, manifest) -> str:
        """Determine security profile based on product features."""
        if manifest.features.get("billing", {}).get("enabled"):
            return "maximum"        # Products handling money = maximum security
        if manifest.features.get("a2a", {}).get("enabled"):
            return "high"           # A2A = lateral movement risk
        return "standard"
```

### Scout Dashboard View

```
┌──────────────────────────────────────────────────────────────────┐
│  Scout; Agent Dashboard                           [Admin] [ 3]│
│                                                                  │
│  Registered Agents                                               │
│  ┌──────────────────────────────────────────────────────────────┐│
│  │ Product    Version  Profile  Status    Signals/24h  Alerts   ││
│  ├──────────────────────────────────────────────────────────────┤│
│  │  AbbiS    1.2.0    MAXIMUM  ONLINE    1,247        2 WARNING:     ││
│  │  Petraclus 1.0.0   HIGH     ONLINE    3,891        7     ││
│  │  FleetZ    0.1.0    STANDARD ONLINE      142        0      ││
│  │  Carina    2.4.0    MAXIMUM  ONLINE    2,103        1 WARNING:     ││
│  └──────────────────────────────────────────────────────────────┘│
│                                                                  │
│  [View All Signals]  [Correlate Across Products]  [Export]       │
└──────────────────────────────────────────────────────────────────┘
```

---

## 2. Per-Product Security Policies

Each product gets its own policy in Scout. The operator sets them. Keprix enforces them.

### 2.1 Policy Definition

```yaml
# Scout → Per-Product Policy (stored in Scout, pushed to Keprix)

product: "petraclus"
security_profile: "high"
version: 2
last_updated: "2026-07-09T10:00:00Z"
updated_by: "operator@verlox.co.uk"

sandbox:
  mode: "docker"                    # docker | host | session_only
  allowed_paths:
    - "/opt/lampp/htdocs/verlox/petraclus/"
    - "/tmp/keprix_sandbox/"
  denied_commands:
    - "rm -rf /"
    - "dd if="
    - "mkfs"
  max_runtime_seconds: 300
  max_output_bytes: 1000000

egress:
  mode: "allowlist"
  allowed_domains:
    - "api.openai.com:443"
    - "api.anthropic.com:443"
    - "api.stripe.com:443"
    - "github.com:443"
    - "pypi.org:443"
    - "api.shodan.io:443"           # Petraclus-specific: threat intel
    - "api.virustotal.com:443"      # Petraclus-specific: malware scan
  dlp_scanning: true
  block_private_ips: true
  block_cloud_metadata: true

tools:
  allowlist_mode: false             # true = only allowlisted tools
  quarantined_tools: []
  dangerous_require_confirmation:
    - "shell-exec"
    - "code-exec"
    - "file-write"
  rate_limits:
    default: { per_minute: 60, per_hour: 500 }
    shell-exec: { per_minute: 10, per_hour: 50 }
    http-request: { per_minute: 30, per_hour: 200 }

governance:
  auto_response_tier: "critical"    # critical | high | off
  auto_suspend_on: 3                # Suspend after 3 critical signals in 10 min
  alert_channels:
    - type: "slack"
      webhook: "https://hooks.slack.com/..."
      min_severity: "high"
    - type: "email"
      address: "security@verlox.co.uk"
      min_severity: "critical"

credentials:
  rotation_interval_days: 90
  vault_audit_enabled: true

audit:
  retention_days: 365
  sync_interval_minutes: 30
  compliance_frameworks: ["SOC2", "GDPR"]
```

### 2.2 Policy Push

Scout pushes policy changes to Keprix via the existing command channel:

```
Scout → Keprix (Redis pub/sub):
  Command: SET_TOOL_POLICY
  Params: { product: "petraclus", policy: { ... } }

Keprix ScoutListener receives → validates → applies immediately
  → Tool policy updated
  → Sandbox mode changed
  → Egress allowlist refreshed
  → Rate limits adjusted
  → ACK sent to Scout
```

---

## 3. Cross-Product Correlation View

Scout's RASP engine correlates signals across products:

```
┌──────────────────────────────────────────────────────────────────┐
│  Scout; Cross-Product Correlation                   [Last 24h] │
│                                                                  │
│  Correlated Attacks Detected: 3                                  │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────────┐│
│  │  COORDINATED INJECTION CAMPAIGN                            ││
│  │    Attacker IP: 203.0.113.42                                 ││
│  │    Pattern: INJ-A (ignore-instructions) + INJ-D (role-hijack)││
│  │    Products hit:                                             ││
│  │       AbbiS; 7 attempts (2 sessions)                ││
│  │       Petraclus; 12 attempts (4 sessions)               ││
│  │       FleetZ; 2 attempts (1 session)                 ││
│  │    MITRE: TA0001 (Initial Access) → TA0004 (Privilege Esc)  ││
│  │    Threat Score: 92/100                                      ││
│  │    Recommended: Suspend all sessions from IP, block /16     ││
│  │    [Suspend All]  [Block IP Range]  [Investigate]           ││
│  └──────────────────────────────────────────────────────────────┘│
│                                                                  │
│  ┌──────────────────────────────────────────────────────────────┐│
│  │ WARNING:   ANOMALOUS TOOL USAGE; Petraclus                        ││
│  │    47 shell-exec calls in 2 minutes (baseline: 3/min)        ││
│  │    Pattern matches credential exfiltration chain              ││
│  │    Cross-check: AbbiS and FleetZ normal                      ││
│  │    [View Session]  [Quarantine Tool]  [Suspend Instance]     ││
│  └──────────────────────────────────────────────────────────────┘│
└──────────────────────────────────────────────────────────────────┘
```

---

## 4. Per-Product Alert Configuration

```python
# keprix/security/scout_alerts.py

class ScoutAlertConfig:
    """
    Per-product alert configuration.

    Each product can configure:
    - Which channels receive alerts
    - Minimum severity for each channel
    - Quiet hours
    - Custom alert rules
    """

    def configure_product_alerts(self, product_id: str, config: dict):
        """Configure alerts for a specific product via Scout API."""

        # Example: Petraclus needs Slack alerts for all HIGH+ events
        # AbbiS needs email only for CRITICAL (billing product)
        # FleetZ needs in-app only for now

        scout_client.send_config(product_id, {
            "alert_channels": config.get("alert_channels", []),
            "quiet_hours": config.get("quiet_hours", {"start": 22, "end": 7}),
            "custom_rules": config.get("custom_rules", []),
        })
```

---

## 5. Product Isolation Guarantees

| Guarantee | How |
|-----------|-----|
| **Signal isolation** | Each signal tagged with `product_id`. Scout filters by product. |
| **Command isolation** | Commands target specific `agent_id`. Broadcast requires operator confirmation. |
| **Credential isolation** | Each product has its own vault namespace. No cross-product credential access. |
| **Policy isolation** | Per-product policies. AbbiS high-security ≠ FleetZ standard. |
| **Audit isolation** | Audit trail tagged with product. Per-product retention policies. |
| **Billing isolation** | Scout billing tracks per-product usage. Each product pays its share. |

---

## 6. Scout Admin API Endpoints

```
# Product management
GET    /api/v1/agents                          List all registered agents
GET    /api/v1/agents/:product_id              Get agent details + current policy
PUT    /api/v1/agents/:product_id/policy        Update security policy
POST   /api/v1/agents/:product_id/command       Send command to agent
GET    /api/v1/agents/:product_id/signals       Query signals for product

# Cross-product
GET    /api/v1/correlation                      Get correlated attack view
GET    /api/v1/correlation/:attack_id           Get specific attack details
POST   /api/v1/correlation/investigate          Trigger cross-product investigation

# Policies
GET    /api/v1/policies                         List all product policies
GET    /api/v1/policies/:product_id             Get specific policy
PUT    /api/v1/policies/:product_id             Update policy
GET    /api/v1/policies/:product_id/history      Policy change history

# Dashboard
GET    /api/v1/dashboard/summary                Operator dashboard summary
GET    /api/v1/dashboard/alerts                 Active alerts across products
GET    /api/v1/dashboard/compliance             Compliance status overview
```

---

## 7. Acceptance Criteria

- [ ] Each Keprix product registers with Scout on boot with unique identity
- [ ] Scout dashboard shows all products with status, signal count, alerts
- [ ] Per-product security policies can be configured and pushed
- [ ] Policy changes take effect within 2 seconds of Scout push
- [ ] Cross-product correlation detects attacks spanning multiple products
- [ ] Alerts can be configured per-product with different channels/severities
- [ ] Product credentials are fully isolated; no cross-product access
- [ ] Scout API endpoints return correct per-product data
- [ ] Product de-registration cleans up gracefully (no orphaned state)
