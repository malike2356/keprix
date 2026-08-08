# Prompt 458 / N08: Multilingual campaigns

**Status: COMPLETED 2026-08-08** (P5 Nice)  
**Series:** 429-465  
**Depends on:** 444, 448, 455 optional  
**Blocks:** none  
**Writing style:** plain ASCII only.

## What was built

- Multilingual Soft Wall locales

## Goal

Multilingual nurture templates with human review and locale-specific compliance notes.

## Must-haves

1. Template locale field (`en-GB`, `fr-FR`, ...); contact preferred locale.
2. Sequence step can select locale variant; fallback to workspace default.
3. Soft Wall required on first publish of each locale variant (human review).
4. Compliance hints per locale (not legal advice): PECR vs other regions flagged in UI.
5. Agent may draft translation; Soft Wall before send enable.
6. Analytics breakdown by locale.
7. Tests: fallback locale; Soft Wall on new locale.

## Acceptance

- [x] FR contact gets FR variant when present
- [x] Missing locale falls back without crash
- [x] Unreviewed locale cannot enroll

## Done When

Cross-border copy is reviewable, not auto-trusted.
