# Troubleshooting

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| 401 / 403 on invoke | Missing/expired token or scope | Re-pair or refresh workload token; check grants |
| Manifest validation fails | Secret-like fields or unknown nodes | Remove secrets; use vault_ref; request only installed nodes |
| Connector timeout | Product down or egress block | Check product health; allowlist host; raise timeout carefully |
| 403 on connector | Undeclared path or mode deny | Add connector declaration; check grants |
| Approval forever pending | UI not deciding / TTL expired | Decide via API; recreate approval after input change |
| Job stuck | Worker budget / kill switch | Check budgets and kill switch; cancel and retry with idempotency key |
| SSE disconnects | Proxy buffering | Disable response buffering for `/events/stream` |
| Port unreachable | Bound to loopback only | Expected for security; use SSH tunnel or private mesh |
| Cross-project data leak suspected | Shared mode misconfigured | Stop shared mode; run isolation matrix; prefer dedicated |

Doctor / conformance reports (when enabled) list deprecations and contract
mismatches.
