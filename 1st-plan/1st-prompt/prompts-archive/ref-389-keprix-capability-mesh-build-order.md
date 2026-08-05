# Ref 389: Keprix capability mesh (build order)

Status: FILED COMPLETED 2026-08-04  
Series living queue: `../pending-prompts/keprix-capability-mesh/`  
Spine: tools.registry + _KEPRIX_CORE_TOOLS / keprix-telegram + shared object IDs + capability graph  
Flagship channel: Telegram (other platforms inherit core tools)

## Order

| ID | File | Intent |
|---|---|---|
| 389 | 00 overview | Guardrails; no second bus |
| 390 | 01 capability graph | Schema + loader + seed |
| 391 | 02 feature DoD | Contract + automated check |
| 392 | 03 gap audit | Nav vs tools vs channels |
| 393 | 04 tool exposure pattern | Companies House recipe |
| 394 | 05 shared object IDs | Pilot link fields |
| 395 | 06 agent discovery | Self-knowledge from graph |
| 396 | 07 Telegram pilot tools | viCal + calendar + contacts |
| 397 | 08 slash + outbound | Telegram UX + reminders |
| 398 | 09 UI related links | Graph-driven deep links |
| 399 | 10 research/memory rollup | Extend mesh |
| 400 | 11 playbooks/skills/cron | Unattended composition |
| 401 | 12 channel parity matrix | Platforms x nodes |
| 402 | 13 tests/docs/archive | Ship gate |

## Parallelism

- 04 can start after 00 (parallel with 01 once overview read).
- 05 after 01; 06 after 01+02.
- 07 needs 04+05 and existing viCal domain.
- 08 after 07.
- 09 after 05+07 (UI can overlap 08).
- 10 and 11 after audit (03) and pattern (04); 11 prefers pilot tools (07).
- 12 after 07/08; 13 last.

## Non-goals

Second capability bus; Channel Shield as router; unbounded root; N×N UI hardcode; new Stripe prices; nesting `carina/verlox/`.
