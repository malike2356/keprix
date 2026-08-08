# Approvals

Human approvals gate propose / mutate / outbound / destructive / high-risk
actions.

## Manifest

```yaml
approvals:
  required_for_risk:
    - propose
    - mutate
    - outbound
    - destructive
    - high_risk
  ttl_seconds: 3600
```

## Flow

1. Node or connector marks `approval_required` or matches a risk class.
2. Sidecar creates an approval with exact action/input hashes.
3. Product UI (or operator) decides via
   `POST /sidecar/v1/projects/{project_key}/approvals/{id}/decision`.
4. Material changes to inputs invalidate the approval.
5. Expired approvals fail closed.

Approvals are scoped, signed, and audited. Playbooks cannot bypass them.
