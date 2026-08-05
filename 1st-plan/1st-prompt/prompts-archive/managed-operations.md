# keprix - Prompt: Managed Operations and Fleet Management

## Purpose

keprix is self-hosted by design, but many users and customers want managed operations: someone else handles upgrades, monitoring, backups, and incident response. This prompt builds the operational backbone for managing multiple keprix instances from a central control plane, whether for internal fleet management or as the foundation for a managed hosting product.

The managed ops layer enables:

- Operators to monitor and manage dozens of keprix instances from one dashboard.
- Customers to offload maintenance while retaining data sovereignty.
- A path to commercial managed keprix hosting without rebuilding the product.

## Scope

Implement:

- Central management dashboard (fleet view).
- Remote health monitoring and alerting.
- Centralized logging aggregation.
- Automated backup scheduling to cloud storage.
- One-click upgrades across fleet.
- SSL certificate lifecycle management.
- Resource usage monitoring and right-sizing recommendations.
- Instance provisioning and decommissioning.
- Audit trail for all operator actions.
- Multi-tenancy boundaries and data isolation guarantees.

## Output Paths

```
keprix/backend/fleet/
  __init__.py
  manager.py              - FleetManager: instance CRUD, health collection, upgrade orchestration
  monitor.py              - health polling, alert rule engine, notification dispatch
  aggregator.py           - log/metric aggregation from managed instances
  provisioner.py          - cloud instance provisioning (AWS, DO, Hetzner)
  scheduler.py            - backup/upgrade/maintenance window scheduling
  ssl_manager.py          - Let's Encrypt automation, expiry monitoring
  audit.py                - operator action audit trail
  schemas.py
  routes.py               - fleet management API endpoints

keprix/backend/fleet/cloud/
  aws.py                  - AWS EC2 provisioning
  digitalocean.py         - DigitalOcean Droplet provisioning
  hetzner.py              - Hetzner Cloud provisioning

keprix/backend/fleet/backup/
  s3.py                   - S3-compatible backup storage
  b2.py                   - Backblaze B2 backup storage
  gcs.py                  - Google Cloud Storage backup storage

keprix/ui/web/src/app/(workspace)/fleet/
  dashboard/              - fleet overview (all instances, health summary)
  instances/              - per-instance detail, logs, metrics
  backups/                - backup scheduling and history
  upgrades/               - upgrade orchestration
  alerts/                 - alert rules and history
  audit/                  - operator audit log viewer

keprix/docs/fleet/
  overview.md
  provisioning.md
  monitoring.md
  backup-strategy.md
  security-model.md

tests/fleet/
  test_manager.py
  test_monitor.py
  test_aggregator.py
  test_provisioner.py
  test_scheduler.py
  test_ssl_manager.py
  test_audit.py
```

## Fleet Dashboard

### Instance overview

A single page showing every managed keprix instance:

| Instance | Version | Status | Uptime | CPU | RAM | Disk | Last Backup | Alerts |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| keprix-prod-1 | 2.1.0 | Healthy | 14d 3h | 23% | 45% | 31% | 2h ago | 0 |
| keprix-staging | 2.1.0 | Healthy | 3d 12h | 8% | 22% | 18% | 6h ago | 0 |
| customer-acme | 2.0.9 | Update avail | 30d 1h | 67% | 78% | 52% | 1d ago | 2 |
| customer-beta | 2.1.0 | Degraded | 5d 8h | 12% | 34% | 28% | 12h ago | 3 |

Colour coding:

- Green: all health checks passing, up to date.
- Yellow: update available, or resource usage above 70%.
- Red: health check failing, or resource usage above 90%.
- Grey: instance unreachable.

Clicking an instance opens its detail view with real-time metrics, logs, and management actions.

### Actions

From the fleet dashboard, an operator can:

- **Upgrade**: roll out a new version to selected instances.
- **Backup now**: trigger an immediate backup.
- **Restart services**: restart all or specific services on an instance.
- **View logs**: stream recent logs from any instance.
- **SSH / console**: open a terminal session to the instance (if configured).
- **Decommission**: safely shut down and archive an instance.

All destructive actions (restart, decommission, upgrade) require confirmation and are audit-logged.

## Instance Connection Model

### Agent-based (preferred)

Each managed keprix instance runs a lightweight fleet agent that:

- Reports health metrics every 60 seconds via WebSocket.
- Accepts commands from the control plane (upgrade, restart, backup).
- Streams logs on demand.
- Authenticates with a per-instance token generated during provisioning.

The agent is optional. Instances without it can still be monitored via HTTP health checks.

### Agentless (fallback)

For instances where the agent cannot be installed:

- Health checks via periodic HTTP requests to `/api/health`.
- Upgrades via SSH command execution.
- Backups via SSH-triggered scripts.
- Logs via SSH tail.

Agentless mode has higher latency and fewer real-time metrics but works with any keprix instance that has SSH access.

### Connection security

- All agent connections use mutual TLS (mTLS).
- Agent tokens are generated per instance, rotatable, and revocable.
- The control plane never stores instance SSH keys. It uses the operator's key forwarded through the dashboard.
- Instance data is encrypted in transit (TLS 1.3) and at rest in the control plane database.

## Health Monitoring and Alerting

### Health poll

The fleet monitor polls every instance on a configurable interval (default 60s):

- `GET /api/health` for overall status.
- `GET /api/health/services` for per-service status.
- `GET /api/health/resources` for CPU, RAM, disk, and swap usage.
- `GET /api/health/version` for current version and available updates.

Failures are recorded with timestamps. Consecutive failures trigger alerts.

### Alert rules

Operators define alert rules per instance or fleet-wide:

```yaml
alert_rules:
  - name: disk_above_80
    condition: disk_used_percent > 80
    severity: warning
    channels: [email, slack]

  - name: instance_unreachable
    condition: health_check_failed_count > 3
    severity: critical
    channels: [email, slack, sms]

  - name: backup_overdue
    condition: hours_since_last_backup > 25
    severity: warning
    channels: [email]

  - name: update_available_over_7d
    condition: update_available_days > 7
    severity: info
    channels: [email]
```

### Notification channels

- Email: SMTP or Postmark.
- Slack: incoming webhook.
- SMS: Twilio.
- Webhook: custom HTTP endpoint.

Alerts are rate-limited: no more than one alert per rule per hour unless severity is critical.

## Centralized Logging

### Log aggregation

Instances stream structured logs to the fleet control plane:

```json
{
  "timestamp": "2026-07-05T12:34:56Z",
  "instance": "customer-acme",
  "service": "backend",
  "level": "ERROR",
  "message": "Database connection pool exhausted",
  "context": {
    "active_connections": 20,
    "max_connections": 20,
    "wait_time_ms": 5230
  }
}
```

### Log retention

- Retain logs for 30 days by default.
- Operators can configure retention per instance (7-365 days).
- Logs older than retention are automatically purged.
- Critical and error-level logs are retained for 90 days regardless of instance setting.

### Log search

The fleet dashboard provides a log search interface:

- Free-text search across all instances.
- Filter by instance, service, level, date range.
- Saved searches for common queries.
- Export to CSV or JSON for external analysis.

## Automated Backup Scheduling

### Backup policies

Operators define backup policies per instance:

```yaml
backup_policy:
  schedule: "0 2 * * *"          # daily at 2 AM UTC
  retention:
    daily: 7                      # keep 7 daily backups
    weekly: 4                     # keep 4 weekly backups
    monthly: 3                    # keep 3 monthly backups
  storage:
    type: s3
    bucket: keprix-backups
    region: eu-west-2
    path: customer-acme/
  encryption: true                # encrypt backups at rest
  verify_after: true              # run verify after each backup
```

### Backup health

The fleet dashboard shows backup status for each instance:

- Last successful backup timestamp.
- Next scheduled backup.
- Backup size and trend.
- Last verify result (pass/fail).
- Storage usage and cost estimate.

Backup failures generate alerts. Consecutive failures escalate severity.

## One-Click Upgrades

### Upgrade orchestration

The fleet manager orchestrates upgrades across multiple instances:

1. Operator selects instances to upgrade and target version.
2. Fleet manager creates an upgrade plan:
   - Order: staging first, then production in batches.
   - Pre-upgrade backup for each instance.
   - Health check before proceeding to next batch.
3. Operator reviews and confirms the plan.
4. Fleet manager executes:
   - Take pre-upgrade backup.
   - Run `keprix update` on the instance.
   - Wait for health checks to pass.
   - If failure: auto-rollback, alert operator, stop the batch.
   - If success: proceed to next instance.
5. Post-upgrade report: success count, failure count, duration, any warnings.

### Canary upgrades

For critical production instances:

- Upgrade one instance first (the canary).
- Monitor for 1 hour (configurable).
- If canary is healthy, proceed with the rest.
- If canary fails, auto-rollback and abort the batch.

### Maintenance windows

Operators can define maintenance windows per instance:

```yaml
maintenance_window:
  day: Sunday
  start: "02:00"
  end: "04:00"
  timezone: Europe/London
```

Upgrades are scheduled within the window. If a window is missed (instance unreachable), the upgrade is deferred to the next window with an alert.

## SSL Certificate Management

### Let's Encrypt automation

The fleet SSL manager handles certificate lifecycle:

- Issue certificates during instance provisioning.
- Auto-renew 30 days before expiry.
- Monitor expiry and alert at 14, 7, and 3 days.
- Handle renewal failures with clear diagnostics.

### Certificate dashboard

Per-instance SSL status:

- Domain(s) covered.
- Issuer (Let's Encrypt, custom).
- Expiry date.
- Auto-renew status.
- Last renewal attempt and result.

## Resource Monitoring and Right-Sizing

### Metrics collected

- CPU: average, peak, trend (7-day, 30-day).
- RAM: used, cached, swap, trend.
- Disk: used, available, growth rate.
- Network: ingress/egress, bandwidth peaks.
- Database: connection count, query latency, size.
- Redis: memory usage, hit rate, key count.

### Right-sizing recommendations

The fleet manager analyses usage patterns and recommends:

- "Instance customer-acme is at 85% RAM. Consider upgrading from 2 GB to 4 GB (estimated +$12/month)."
- "Instance keprix-staging averages 8% CPU. Consider downgrading from 2 vCPU to 1 vCPU (save $8/month)."
- "Disk usage on customer-beta is growing at 2 GB/week. At this rate, disk will be full in 6 weeks."

### Resource limits and quotas

For managed hosting scenarios:

- Set per-instance resource limits (CPU, RAM, disk, bandwidth).
- Alert when approaching limits; throttle when exceeding.
- Bill based on actual usage or fixed tiers.

## Instance Provisioning

### One-click provision

From the fleet dashboard, "New Instance":

1. Choose provider: AWS, DigitalOcean, Hetzner, or custom (SSH target).
2. Choose plan: size, region, OS image.
3. Choose keprix version (default: latest stable).
4. Configure domain and SSL.
5. Set initial admin credentials (auto-generated or specified).
6. Provision.

The provisioner:

- Creates the cloud instance via provider API.
- Waits for SSH to become available.
- Runs the keprix install script.
- Registers the instance with the fleet.
- Runs initial health checks.
- Returns the access URL and admin credentials.

### Decommissioning

Safely remove an instance:

1. Take a final backup.
2. Stop all keprix services.
3. Archive data to long-term storage (optional, configurable retention).
4. Destroy the cloud instance (or leave it running for SSH-only instances).
5. Remove from fleet dashboard.
6. Audit log the decommission with operator identity and timestamp.

## Audit Trail

### What is logged

Every operator action is recorded:

- Who (operator identity).
- What (action: upgrade, backup, restart, provision, decommission).
- When (timestamp with timezone).
- Which instance(s).
- Result (success, failure, partial).
- Context (version numbers, error messages, duration).

### Audit log viewer

The fleet dashboard includes an audit log with:

- Chronological view of all actions.
- Filter by operator, instance, action type, date range.
- Export for compliance.
- Immutable: audit logs cannot be deleted or modified.

### Retention

Audit logs are retained for the lifetime of the fleet control plane (minimum 1 year for compliance).

## Multi-Tenancy and Data Isolation

### Tenant boundaries

For managed hosting where multiple customers share infrastructure:

- Each customer's keprix instance runs in its own Docker network or VM.
- Database per instance (never shared databases between customers).
- Volume per instance for data storage.
- No cross-instance network access unless explicitly configured.

### Operator access control

- Operators authenticate with the fleet control plane (not directly to customer instances).
- Role-based access: admin (full fleet), operator (assigned instances only), viewer (read-only).
- Customer data is never accessible to operators without explicit customer consent and audit logging.
- Sensitive actions on customer instances require a reason field.

### Data sovereignty

- Instances can be provisioned in specific regions to meet data residency requirements.
- Backups are stored in the same region by default.
- Instance data never leaves its provisioned region without explicit configuration.

## Tests

```
tests/fleet/
  test_manager.py           - instance CRUD, health collection
  test_monitor.py           - health polling, alert rule evaluation
  test_aggregator.py        - log aggregation, retention policies
  test_provisioner.py       - cloud provisioning, decommissioning
  test_scheduler.py         - backup scheduling, upgrade orchestration
  test_ssl_manager.py       - certificate lifecycle, renewal
  test_audit.py             - audit logging, immutability
  test_backup_s3.py         - S3 backup storage integration
  test_alert_rules.py       - rule evaluation, rate limiting, channels
  test_upgrade_canary.py    - canary upgrade flow, auto-rollback
  test_multi_tenant.py      - tenant isolation, access control
```

## Acceptance Criteria

- Fleet dashboard shows all managed instances with real-time health status.
- Alert rules fire within 60 seconds of condition being met and respect rate limits.
- One-click upgrade upgrades staging first, waits for health checks, then proceeds to production.
- Failed upgrade auto-rollbacks and the operator is alerted.
- Backup schedule runs on time, verifies after completion, and alerts on failure.
- SSL certificates auto-renew 30 days before expiry.
- Right-sizing recommendations are based on at least 7 days of usage data.
- All operator actions are audit-logged and immutable.
- Customer instances are fully isolated: no shared databases, no cross-instance network access.
- Provisioning a new instance on AWS/DigitalOcean/Hetzner completes within 5 minutes.
