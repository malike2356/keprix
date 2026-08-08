# Clinical safety hazard log
| Hazard | Owner | Controls | Detection | Residual risk |
| --- | --- | --- | --- | --- |
| Mistranslation | Clinicom clinical owner | Preserve numbers and negation; human review | Golden replay and preservation warnings | Medium |
| Omitted negation | Keprix pack owner | Negation extraction and review flag | `possible_negation_loss` | Medium |
| Dosage distortion | Keprix pack owner | Numeric preservation checks; no dosing advice | `possible_number_loss` | Medium |
| Wrong speaker or language | Clinicom product owner | Explicit language and speaker metadata | Session validation and operator review | Medium |
| Delayed audio | Platform operator | Bounded payloads, timeout, labelled degradation | Latency metrics and queue alerts | Medium |
| Unsafe simplification | Clinicom clinical owner | Preserve terms and no diagnosis or prescribing | Golden fixtures and clinician acceptance | Medium |
| Overconfident triage | Clinicom clinical owner | Bounded category signal only; no disposition | Safety escalation metric | Medium |
| Hallucinated medication | Keprix pack owner | Approved glossary and unknown-term flags | Glossary warning and review | Medium |
| Failed human escalation | Clinicom product owner | Proposal-only output and explicit acceptance | Audit event and workflow monitoring | Medium |
