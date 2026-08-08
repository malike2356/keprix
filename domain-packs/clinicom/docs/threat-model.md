# Threat model
| Threat | Control |
| --- | --- |
| Patient leakage | Purpose-limited context excludes identity, NHS number, address, EHR, and full history. |
| Cross-organisation access | Product connector derives organisation from authenticated session and fails closed. |
| Prompt injection | Utterances are treated as data and injection signals are flagged, not executed. |
| EHR overreach | Sidecar and connector are proposal-only; EHR writes are prohibited. |
| Malicious audio | MIME allowlist and size validation apply before provider calls. |
| Token replay | Short-lived memory-only service tokens are scoped to organisation and session. |
| Model retention | Do not log raw utterance or audio; providers require approved retention controls. |
| OPS boundary | Clinicom OPS remains separate from Carina, Aiva, and Scout operations. |
