# Agentic OS adoption build order (Keprix 256-265)

**Master reference:** `255-agentic-os-adoption-master-reference.md`  
**Source video:** `planning/competitor-research/youtube-HRw-vP0j8OM-transcript.txt`

---

## Critical path

```text
256 (audit) --> 257 (session-to-skill)
                    |
                    +--> 260 (promoter) --> 262 (action board) --> 263 (client kit)
                    |
                    +--> 261 (run ledger) ----^

258 (workspace map) --> 259 (vault)
264 (starter pack) after 256+258
265 (onboarding) last; checklist stubs OK until peers ship

Parallel anytime: KNIME 233-238, Scout 236, credentials 239-243
```

---

## Prompt order

| Order | Prompt | Title | Depends on | Status |
| --- | --- | --- | --- | --- |
| 1 | **256** | Workflow audit wizard | none | Shipped |
| 2 | **257** | Session-to-skill automation loop | **256** (soft) | Shipped |
| 2b | **258** | Structured workspace memory | none | Shipped |
| 3 | **259** | Universal vault provider | **258** | Shipped |
| 4 | **260** | Skill-to-automation promoter | **257** | Shipped |
| 4b | **261** | Playbook run ledger + loop profiles | **257**, playbooks | Shipped |
| 5 | **262** | Headless action board | **260**, **261** | Shipped |
| 6 | **263** | Client kit + simplified mode | **262** | Shipped |
| 6b | **264** | Personal OS starter pack | **256**, **258** | Shipped |
| 7 | **265** | Agentic OS onboarding checklist | **256-264** (feature flags) | Shipped |

**Pack status:** prompts **256-265** shipped and archived on 2026-07-09.

---

## Minimum viable Agentic OS (demo story)

Ship **256 + 257 + 258 + 262** for a Chase-style demo without waiting for full pack:

- Guided workflow audit
- Session pattern proposes a skill
- Knowledge Pipeline workspace with indexes
- One-click headless skill run from action board

Add **260 + 261** for automation ladder + loop engineering. Add **263-265** before client handoff.

---

## Week plan (suggested)

| Week | Prompts | Outcome |
| --- | --- | --- |
| 1 | 256, 258 | Audit entry + workspace map |
| 2 | 257, 259 | Skill loop + vault |
| 3 | 260, 261 | Promoter + run ledger |
| 4 | 262, 263, 264, 265 | Action board, client kit, pack, onboarding |

KNIME **233** can run week 2-3 in parallel with **257-261**.

---

## Cross-product rules

1. **No second agent runtime.** Headless runs use existing `AIAgent` / playbook runner / Agent Apps runner.
2. **No Obsidian plugin in core.** Vault is folder-based; Obsidian is optional editor.
3. **No vanity metrics.** Action board shows run health, tokens, approvals, schedules; not social stats.
4. **Scout governs publish** via **236**; Agentic OS pack feeds events, does not execute in Scout.
5. **Operator copy:** skill, playbook, Agent App (not "Agentic OS workflow").

---

## Archive order

When each prompt AC passes, archive to `prompts-archive/`. Update `PROMPT-IMPLEMENTATION-AUDIT.md` and master reference status table.

When **all** 256-265 pass, add row to `planning/competitor-research/` adoption index marking Chase Agentic OS pack shipped.
