# Threat model

| Scenario | Trust | Risks | Mitigations |
| --- | --- | --- | --- |
| Local same host | Loopback + pairing | Local malware; misbind `0.0.0.0` | Default `127.0.0.1`; refuse public bind without TLS/auth |
| Docker network | Private compose net | Container escape; SSRF to metadata | NetworkPolicy; connector IP allowlists; no host docker.sock |
| Remote private network | mTLS or short-lived tokens | Token theft; confused deputy | Audience binding; grant ceilings; audit |
| Reverse connect | Project initiates outbound | Stale work after cancel; grant smuggling | Same grant ceiling; idempotency; cursor |
| Air gap | Offline bundle, no telemetry | Stale signed packs; unsigned extensions | Signed wheels/images; no hidden update calls |

Additional threats: prompt injection from product content, forged tokens,
replayed webhooks, and oversized payloads. Controls: untrusted-data handling,
signature + skew checks, body limits, schema validation.
