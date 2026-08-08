# Production hardening

1. Dedicated sidecar per product deployment (preferred).
2. Bind privately (`127.0.0.1` or ClusterIP); TLS or mTLS in transit.
3. No public anonymous invoke endpoint.
4. Strict request/body/file limits and schema validation.
5. SSRF and egress allowlists for every URL.
6. Prompt-injection controls: treat product and fetched content as untrusted.
7. Tool output validation and policy recheck before every side effect.
8. No shell/browser/network/filesystem/mutation nodes unless explicitly
   allowlisted and sandboxed.
9. Immutable audit for token exchange, reads, inference, tools, approvals,
   actions, denials, exports, retention, and admin config.
10. Per-product, tenant, node, and provider kill switches.
11. Budgets: RPM, concurrent jobs, tokens, cost, callbacks, storage.
12. Signed packs; dry-run upgrades; retain last-known-good.

See also [security-checklist.md](security-checklist.md) and
[threat-model.md](threat-model.md).
