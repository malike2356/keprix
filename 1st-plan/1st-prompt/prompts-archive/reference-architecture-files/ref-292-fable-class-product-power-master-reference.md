# Fable-class product power (Keprix 292-297)

**Status:** Pending  
**Source insight:** Anthropic Claude Fable 5 / Mythos 5 product prompt (`competitor-research/00-agents-to-adopt/major-llm-leak/Anthropic/claude-fable-5.md`)  
**Related shipped:** Layered prompts **289**, provider-agnostic tools **291**, personas **290**, Hermes progressive tools **280**, Scout/governance **278-283**, defense-in-depth **275**

---

## Strategic claim

Fable 5 feels powerful because of **model + agent product surface**, not because of its refusal essay.

Fable and Mythos share the same underlying model. Fable adds dual-use safety measures; Mythos removes those for approved orgs. Keprix cannot invent Mythos-class weights from a markdown file. Keprix **can** match and in places exceed the **product** power by deepening:

1. Skills (skill-first execution)
2. Computer use (real deliverable paths)
3. Deferred tools (`tool_search` as default at scale)
4. Memory (colleague continuity, not narrated retrieval)
5. MCP (connector-first routing)
6. **Operator-owned policy** (Scout/product config owns refusal strictness; kernel stays capable)

---

## Non-goals

- Do not port the full Fable system prompt verbatim.
- Do not treat "fewer refusals" as a capability upgrade.
- Do not remove child-safety or clear-harm hard floors from the kernel.
- Do not duplicate **289** layered prompt work; extend it with execution contracts.
- Do not rebuild Scout; wire policy profiles into the agent loop.

---

## Capability map

| Area | Fable pattern | Keprix today | Gap this pack closes |
| --- | --- | --- | --- |
| Skills | Read `SKILL.md` before code/files/bash | Skills hub, preprocessing, optional skills | Mandatory skill-first gate + audit |
| Computer | Scratch `/home/claude`, outputs `/mnt/user-data/outputs`, `present_files` | `computer_use`, terminal, file tools | Unified deliverable contract + present path |
| Tools | Deferred catalog + `tool_search` | `tools/tool_search.py` exists | Default-on at scale, schema accuracy, metrics |
| Memory | Silent colleague recall + past chat tools | Workspace memory, vault, hot cache | Continuity etiquette + search-before-ask |
| MCP | Prefer connected tools; suggest connectors | MCP discovery, admin, manifests | Connector-first router before browser |
| Policy | Anthropic-hardcoded Fable vs Mythos | `product_policy.py`, Scout, tool ACL, egress | Operator profiles: strict / standard / permissive |

---

## Hard floors (always on)

These are not "user restrictions to remove." They stay in the kernel regardless of operator profile:

- Child safety
- Clear instructions for weapons / explosives production
- Malware and exploit tooling intended to cause harm
- Operator kill switch / Scout lockdown when enabled

Everything else (dual-use research depth, coding aggressiveness, browser autonomy, package install) is **operator-owned**.

---

## Prompt index

| # | Title | Primary deliverable |
| --- | --- | --- |
| **292** | Skill-first execution contract | Gate: view relevant SKILL.md before file/code/bash |
| **293** | Computer-use deliverable paths | Scratch vs outputs vs present_files contract |
| **294** | Deferred tool search hardening | Default deferred tools + bridge metrics |
| **295** | Colleague memory continuity | Silent recall + past-chat search etiquette |
| **296** | MCP connector-first routing | Prefer MCP; suggest connect; browser last |
| **297** | Operator-owned policy kernel | Profiles wired into layered safety + tool ACL |

Build order: `292-fable-class-product-power-build-order.md`.

---

## Success metric

Measure **task completion**, not refusal rate:

- Multi-step coding with skill-guided output quality
- Doc/pptx/xlsx/pdf deliverables that land in outputs and are presentable
- Sessions with 50+ tools available without blowing the tools budget
- "Continue where we left off" without the user re-explaining
- Connected Gmail/Drive/Calendar used before browser scraping
- Operator can switch `strict` ↔ `permissive` without redeploying the model

---

## Contact

Verlox Ltd: [contact@verlox.uk](mailto:contact@verlox.uk)
