# Audit log

Security-relevant actions are recorded locally and may forward to Scout when enabled.

## Configuration

```bash
KEPRIX_AUDIT_FAIL_ON_HIGH=false
KEPRIX_REDACT_PRIVATE_IPS=false
```

## Scout bridge

When `KEPRIX_GOVERNANCE_ENABLED=true`, events queue for delivery. See [Scout integration](../integrations/scout.md).

## Review

Admin diagnostics and Scout governance UI list recent events.
