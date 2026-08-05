# Quotas

Stub for product and actor quotas: day/month counters, admin overrides, and denial audit (`quota_denied` / `actor_quota_denials`).

| Surface | Purpose |
| --- | --- |
| `GET /api/quotas/status` | Signed-in user quota status |
| `/api/admin/quotas/*` | Product quotas, actor overrides, scheduler stats, denial list |

When an actor quota blocks a run, the run ledger and security audit record the denial. See [Agent OS run ledger](agent-os-run-ledger.md).

## Related

- [Billing](billing.md)
- [Resource-scoped tool ACL](resource-tool-acl.md)
- [Readiness](../operations/readiness.md)
- [API reference](../reference/api.md)
