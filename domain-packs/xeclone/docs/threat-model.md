# Xeclone threat model

## Assets

- Owner biometric/likeness media
- Voice samples
- Private correspondence and relationship notes
- Channel OAuth tokens (product-held)
- Public brand reputation

## Threats

1. Deepfake misuse / impersonation of another person
2. Private-message impersonation
3. Biometric theft via provider upload
4. Relationship leakage into public drafts
5. Voice replay fraud / payment social engineering
6. Prompt injection in personal archives
7. Poisoned training data
8. Cross-tenant memory retrieval
9. Unauthorised publishing or approval bypass
10. Forged consent records
11. Watermark/disclosure removal
12. Shadow dual-run accidentally publishing

## Controls

- Consent ledger with revoke
- Subject must match owner for identity input
- Generation separated from distribution
- Shadow never publishes
- Kill switch on publish/media
- Scout redacted audit
- Deterministic adversarial evals
- Connector default deny
- No OAuth on bridge
- Autonomous mode OFF
