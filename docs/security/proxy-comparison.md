# Cordon vs Keprix Proxy

| Factor | Cordon external | keprix-proxy built-in |
| --- | --- | --- |
| Setup time | 2 minutes with `cordon setup hermes` | 5 minutes with `keprix proxy setup` |
| Vault support | 1Password, OS keychain | Bitwarden, 1Password, OS keychain |
| Fleet-aware | No, local only | Yes, designed for Keprix fleet work |
| Audit integration | Basic proxy logs | Keprix credential audit trail |
| Rotation scheduling | No | Reminders, cache invalidation, grace path |
| Maintenance burden | CodeZero maintains it | Keprix team maintains it |
| Offline or air-gapped | Requires npm install | Ships with Keprix |
| Recommendation | Individual developers, quick start | Production deployments and fleet operators |
