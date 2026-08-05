# Keprix Prompt 367: Hermes parity + surpass re-proof and comparison closeout

## Purpose

Re-run and document Hermes behavior parity and TUI surpass proof so private
ship claims are evidence-backed, not archival memory.

## Tasks

1. Run and capture evidence:
   - `bash scripts/check-tui-parity.sh`
   - `bash scripts/check-tui-surpass-hermes.sh`
   - `bash scripts/check-agent-parity.sh`
2. Update `docs/architecture/keprix-agent-parity-report.md`:
   - Refresh date and evidence counts
   - Keep deliberate differences (Textual vs Ink, Channel Shield gateway, branding)
   - Explicitly state comparison/surpass status for TUI
3. Add or refresh a short operator-facing comparison section in
   `docs/features/tui.md` pointing at parity + surpass contracts and the three
   check scripts.
4. If any gate fails, fix the contract or implementation before ship; do not
   weaken the gate.

## Verification

```bash
bash scripts/check-tui-parity.sh
bash scripts/check-tui-surpass-hermes.sh
bash scripts/check-agent-parity.sh
rg -n 'surpass|parity|100/100|10/10' docs/architecture/keprix-agent-parity-report.md docs/features/tui.md
```
