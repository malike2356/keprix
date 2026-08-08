# Security checklist

Operator checklist before production:

- [ ] Sidecar bound privately (loopback / ClusterIP / private DNS)
- [ ] TLS or mTLS enabled; no anonymous public invoke
- [ ] Pairing codes one-time; bootstrap secrets in vault only
- [ ] Short-lived tokens with audience and grant ceilings
- [ ] Manifest has no embedded secrets or executable hooks
- [ ] Connectors default-deny; every path declared
- [ ] Egress allowlist; loopback/private only when intentional
- [ ] SSRF blocked (metadata hosts, blocked schemes)
- [ ] Approvals for propose/mutate/outbound/destructive/high_risk
- [ ] Budgets and kill switches configured and tested
- [ ] Audit retention meets policy; logs redacted
- [ ] Deletion/retention propagation tested
- [ ] Prompt-injection and oversized-request tests pass
- [ ] Isolation tests pass (no cross-tenant / cross-project)
- [ ] Product core remains usable with sidecar down
- [ ] Vulnerability reports go to private channel (see SECURITY.md)
