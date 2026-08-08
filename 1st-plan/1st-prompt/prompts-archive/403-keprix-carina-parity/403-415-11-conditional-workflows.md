# Prompt 414 / 11: Conditional workflows

Status: COMPLETED 2026-08-04
Series: Keprix close Carina parity gaps  
Depends on: 410 / 07  
Blocks: 415  
Severity: LOW  
Writing style: plain ASCII only (no em/en dashes, no emoji).

## Why this exists

Carina workspace automations support richer if/then. Keprix has triggers/cron/skills; need first-class condition composability for mesh events (booking confirmed -> notify -> create lead).

## Goal

Extend trigger engine with a small condition DSL (status equals, field present) and one shipping template for viCal confirmed -> send_message / create_lead.

## Must-haves

1. Condition evaluator + tests.
2. Template workflow documented and runnable in dry-run.
3. Mesh graph edge notes.

## Acceptance

- [x] Dry-run fires action when condition matches fixture event.
