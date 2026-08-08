# Xeclone architecture (XCS-00)

## Inventory (Wave 0)

| Area | Owner | Notes |
| --- | --- | --- |
| Persona files | Xeclone + pinned artifact | `personas/ilaud.yaml` at `ilaud@0.1.0` |
| Identity assets | Xeclone | Asset registry references only; raw biometrics stay product-controlled |
| Consent ledger | Xeclone + sidecar check | Versioned, revocable purposes |
| Carina worker | Carina | Phase 1 live inbound/OAuth path |
| OAuth channels | Product / Carina | Never copied into Keprix bridge requests |
| Approvals UI | Product / Carina | Keprix drafts hand off without changing inbound |
| Scout | Keprix events | Hashes + redacted metadata |
| Providers | Stub in Wave 1 | Deterministic fallback to text-only drafts |

## Responsibilities

1. **Xeclone**: identity assets, consent, product UX, channel accounts, approvals.
2. **Keprix**: persona runtime, scoped RAG, multimodal jobs, playbooks, kill switch.
3. **Carina**: Phase 1 live paths until cut over; Wave 0 must not change live Carina/Aiva.

## Risk classes

- private draft
- owner conversation
- public content draft
- voice
- likeness image
- talking-head video
- account publish
- private reply
- autonomous engagement (OFF)

Publishing and private reply are always separately gated initially.

## Migration waves

| Wave | Entry | Exit | Rollback | Ownership |
| --- | --- | --- | --- | --- |
| 0 | Architecture + pack | Docs and nodes signed | N/A (no live change) | Architecture |
| 1 | Keprix draft memory only | Shadow quality gates | Disable Keprix draft path | Keprix drafts / Carina live |
| 2 | Inbound + vault migration | Replay tests pass | Revert ingress to Carina | Shared |
| Later | Autonomous mode | Separate owner sign-off | Kill switch + disable flag | Owner |

Wave 0 preserves Carina: this pack never changes the live Carina/Aiva runtime path.

## Threat model summary

Deepfake misuse, private-message impersonation, biometric theft, relationship
leakage, voice replay fraud, prompt injection in personal archives, poisoned
training data, cross-tenant memory, and unauthorised publishing. See
`threat-model.md`.
