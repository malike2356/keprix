# Prompt 408 / 05: Scout Warden integration into Keprix

Status: COMPLETED 2026-08-04
Series: Keprix close Carina parity gaps  
Depends on: 407 / 04  
Blocks: 415  
Severity: HIGH  
Writing style: plain ASCII only (no em/en dashes, no emoji).

## Why this exists

Carina Labyrinth Scout Warden is a full scanning engine. Keprix has Scout extension + kill relay. Need a safe integration path without embedding Scout's entire stack in CE by default.

## Goal

Wire Keprix to call Scout Warden APIs / events for scan-on-demand and alert ingest, gated by env, with Channel Shield-compatible agent-safe summaries.

## Baseline

`keprix/src/keprix/extensions/scout/`, Carina Scout under canonical backends. Soft separation: Aiva is Carina product surface.

## Must-haves

1. Config: Scout base URL + auth from `.access` / env (no secrets in repo).
2. Tool or admin API: request scan, fetch status (mocked tests).
3. Alert ingest -> security finding row or notification.
4. Docs runbook + disable-by-default for CE.

## Acceptance

- [x] With Scout unreachable, Keprix degrades honestly (no crash).
- [x] Mocked scan round-trip test green.
