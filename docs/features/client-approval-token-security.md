# Client approval and token security

Stub for first-seen remote client approval on hosted deployments. API keys used by remote kits and agent clients are fingerprinted; unknown clients require operator approve/deny before use. Token security events are audited.

UI: Developer platform **Client approvals** at `/developer`. Module: `keprix.security.client_approval`.

## Related

- [Developer platform](developer-platform.md)
- [Agent OS client kit](agent-os-client-kit.md)
- [Readiness](../operations/readiness.md) (client approval gate)
- [API reference](../reference/api.md)
