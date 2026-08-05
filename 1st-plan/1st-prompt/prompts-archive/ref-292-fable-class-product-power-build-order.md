# Fable-class product power build order (Keprix 292-297)

**Master reference:** `292-fable-class-product-power-master-reference.md`  
**Source:** `competitor-research/00-agents-to-adopt/major-llm-leak/Anthropic/claude-fable-5.md`

---

## Critical path

```text
292 (skill-first) ----+
                      |
293 (computer paths) -+--> 294 (deferred tools) --> 296 (MCP routing)
                      |
295 (memory) ---------+
                      |
297 (operator policy) binds all of the above (can start in parallel after 292)
```

---

## Prompt order

| Order | Prompt | Title | Depends on | Parallel OK? |
| --- | --- | --- | --- | --- |
| 1 | **292** | Skill-first execution contract | **289** layered prompt | - |
| 2 | **293** | Computer-use deliverable paths | **292** (skill read before file create) | Yes with 295 |
| 2b | **295** | Colleague memory continuity | Workspace memory / vault | Yes with 293 |
| 3 | **294** | Deferred tool search hardening | **291**, existing `tool_search.py` | After 292 |
| 4 | **296** | MCP connector-first routing | **294** (tools surface), MCP stack | - |
| 5 | **297** | Operator-owned policy kernel | **275**, Scout product policy, **292-296** hooks | Start stub early; finish last |

---

## Minimum viable demo

Ship **292 + 293 + 294**:

1. Ask for a PowerPoint / report / chart: agent reads skill first, writes to outputs, presents file.
2. Session with large tool catalog: core tools visible; deferred tools load via `tool_search`.
3. Operator profile `standard` still blocks malware; `permissive` allows deeper dual-use research discussion without disabling sandboxes.

Add **295** for continuity demo; **296** for connector-before-browser; **297** for profile switch UI/CLI.

---

## Parallel with other packs

| Track | Relationship |
| --- | --- |
| **289-291** Fable prompt/tools/personas | This pack is the execution surface on top |
| **275** Defense-in-depth | Sandboxes/gates stay; **297** selects profile |
| **278-283** Scout | Policy profiles emit Scout signals; kill switch unchanged |
| **280** Hermes progressive tools | **294** hardens and defaults the same idea |
| Agentic OS / Chase / Nate | Skills and memory already exist; do not duplicate hubs |

---

## Contact

Verlox Ltd: [contact@verlox.uk](mailto:contact@verlox.uk)
