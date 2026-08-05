# AI security delta (Carina vs Keprix)

| Carina control | Keprix status | Notes |
|---|---|---|
| Fail-closed prompt guard | Done (372-375) | `prompt_guard_policy` |
| RAG / Graphiti poison gate | Done | `ingest_poison_gate` |
| Rule of Two health | Done | health surfaces |
| Output canary tokens | Added | `ai_hardening.canary_*` (opt-in via env) |
| Tool-call schema strictness | Added | `validate_tool_args` for mesh tools |
| Anomaly counters | Added | `record_anomaly` / snapshot |
| Deep output filtering | Partial | reuse prompt_guard patterns on egress paths later |

Do not regress KEPRIX_PROMPT_GUARD defaults from 372-375.
