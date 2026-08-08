# Prompt CLS-04: Clinicom clinical evaluations, human controls, and degradation

**Status: COMPLETED 2026-08-08**
**Depends on:** CLS-01, CLS-02
**Blocks:** CLS-05

## Goal

Prove useful communication assistance across languages and specialties while
keeping clinicians and patients informed and in control.

## Must-haves

1. Expand golden corpus across language pairs, accents/audio quality, numbers,
   dates, dose/frequency, allergies, symptoms, negation, consent, safeguarding,
   cultural context, Easy Read and specialty terminology.
2. Score semantic preservation, critical-term accuracy, number/negation accuracy,
   omission/addition, readability, latency, confidence calibration and human edit.
3. Compare Keprix to Carina and deterministic fallback with paired blinded review.
   Define non-inferiority and hard safety thresholds per tool before shadow pilot.
4. User controls: original/transformed view, replay, confidence/warnings, provider
   state, accept/edit/reject, retry, human interpreter/handoff and report issue.
5. Low confidence, conflicting language, poor audio, critical term uncertainty,
   safety signal or provider degradation triggers clarification or human escalation,
   not polished overconfidence.
6. Teach-back score and HCI outputs are assistance/quality measures, not patient
   capability judgements. Prevent discriminatory or clinical use beyond policy.
7. Adversarial tests include instructions inside utterances, medication fabrication,
   identity request, diagnosis request, self-harm/emergency wording, abusive content,
   oversized audio, malformed encoding and cross-session ids.
8. Degraded drills prove continuity with local clone/deterministic path and accurate
   UI capability/status labels.

## Acceptance

- [ ] Hard safety thresholds pass for every advertised live tool
- [ ] Low-confidence path visibly escalates or clarifies
- [ ] Clinician edit/reject feeds quality metrics without unsafe auto-training
- [ ] No tool claims diagnosis, prescription or clinical disposition

## What was built

- Golden fixtures, clinical safety tests, eval thresholds
- Human controls and degraded-operation docs
