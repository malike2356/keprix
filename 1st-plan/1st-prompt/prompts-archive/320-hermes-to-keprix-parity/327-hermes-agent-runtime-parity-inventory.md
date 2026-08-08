# Keprix Prompt 327: Hermes Agent Runtime Parity Inventory

## Purpose

Create a precise inventory of agent runtime behavior in Hermes and Keprix before changing code. This prevents blind porting and protects Keprix extensions.

## Tasks

1. Compare Hermes and Keprix across these areas:
   - agent loop
   - tool dispatch
   - prompt assembly
   - provider routing
   - streaming
   - retry and recovery
   - session persistence
   - memory
   - checkpoints
   - file edits
   - terminal execution
   - approval flow
   - skills
   - plugins
   - MCP
   - gateway
   - cost and rate handling
2. Create `docs/architecture/hermes-agent-parity-inventory.md`.
3. For each area, classify Keprix status:
   - same
   - Keprix better
   - Hermes better
   - missing
   - different by design
   - blocked by product boundary
4. Include file references from both trees for every claim.
5. Identify Keprix extensions that must not be removed.

## Required output table

| Area | Hermes files | Keprix files | Status | Action |
| --- | --- | --- | --- | --- |

## Do not change

Do not port code in this prompt. This prompt is inventory and decision capture only.

## Acceptance criteria

- The inventory identifies exact files to modify in later prompts.
- The inventory identifies exact Keprix features that must be preserved.
- The inventory separates core parity gaps from product-layer differences.

## Verification

```bash
python3 ../scripts/fix-writing-style.py
rg -n "Hermes|Keprix|parity" docs/architecture/hermes-agent-parity-inventory.md
```
