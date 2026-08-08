# Petraclus sidecar threat model

## Assets

Authorised target grants, finding truth, redacted evidence, licences, audit trails, report drafts.

## Threats and controls

| Threat | Control |
| --- | --- |
| Forged target grants | Product-signed grants; revalidate expiry/revocation before each active action |
| SSRF / metadata IPs | Reject internal/link-local/metadata unless grant explicitly names them |
| Prompt injection in banners/findings/feeds | Detect patterns; treat as data; never trigger tools from injected text |
| Malicious scan output | Sanitize; size caps; provenance labels |
| Command injection | No shell / free-form nmap / exploit nodes |
| Cross-workspace findings | IsolationEnforcer workspace layer; fail closed |
| Licence bypass | Entitlements only from Petraclus; Keprix cannot mint or extend grace |
| Secret leakage | Redacted evidence default; never log tokens/findings/raw evidence |
| Poisoned feeds | feed_item_assess marks injection; no auto remediation |
| Report exfiltration | Publish gated; minimum necessary ticket fields |
| Agent escalation via playbooks | Read-only grants without mutate cannot run action nodes |

## Residual risk

Staging pilot must use fixture or owned test assets only. No public/live target scans from this pack's tests.
