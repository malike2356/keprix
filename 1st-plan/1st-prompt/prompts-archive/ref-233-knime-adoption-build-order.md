# KNIME adoption build order (Keprix 233-238 + Carina knime-adoption)

**Master reference:** `233-knime-adoption-master-reference.md`  
**Competitive note:** `planning/competitor-research/knime-visual-workflow-adoption.md`  
**Carina prompts:** `carina/01-devends/prompts-library/pending/knime-adoption--*.md`

---

## Keprix series (233-238)

**Status:** Complete and archived on 2026-07-09.

| Order | Prompt | Title | Depends on | Status |
| --- | --- | --- | --- | --- |
| 1 | **233** | Visual Playbook Studio | Runtime 207-211 (shipped) | Shipped |
| 2a | **234** | Connector catalog marketplace | Hub 36, MCP 210, **233** for studio link | Shipped |
| 2b | **236** | Scout publish + telemetry | **233** publish stub | Shipped |
| 3 | **237** | Templates, variables, coach | **233** | Shipped |
| 4 | **235** | Community vs Enterprise gates | SSO/fleet 214-219; **234** governance hooks | Shipped |
| 5 | **238** | Import bridges + run overlay | **233**, n8n 207 | Shipped |

### Critical path

```text
233 (studio) --> 237 (citizen analyst polish)
     |               |
     +--> 234 (connectors) --> Carina 04
     |
     +--> 236 (Scout events) --> Carina 03
     |
     +--> 238 (import/overlay)

235 (editions) parallel anytime after 233; wire org publish before 236 org flow goes live.
```

### Minimum viable KNIME parity (MVP)

Ship **233 + 234 + 236** for demoable KNIME-style story:

- Visual authoring
- Connector marketplace
- Scout publish + run metrics

Prompts **237 + 238** add the citizen analyst and migration story. **235** supplies the enterprise sales gating model.

---

## Carina series (knime-adoption)

| Order | Prompt | Title | Blocked by |
| --- | --- | --- | --- |
| 0 | **00** | Architecture reference | Read only |
| 1 | **03** | Scout agent lifecycle | None (ingest events; stub until 236) |
| 2 | **233** | (Keprix) Studio | Carina 01, 02 |
| 3 | **01** | Agent Studio embed | Keprix 233 URL + APIs |
| 4 | **02** | Aiva property starter | Keprix 233 + 237 template |
| 5 | **05** | Worker playbook runner | Keprix 233 + 02 template id |
| 6 | **04** | Integrations hub | Keprix 234 API (stub ok) |

### Recommended parallel plan

| Week | Keprix | Carina |
| --- | --- | --- |
| 1 | 233 | 03 (event schema + dashboard shell) |
| 2 | 234 + 236 | 01 embed |
| 3 | 237 | 02 Aiva template + 05 runner |
| 4 | 238 + 235 | 04 integrations |

---

## Cross-product rules

1. **One runtime (Keprix), one studio (Keprix), two surfaces (Keprix workspace + Carina embed).**
2. **Scout governs publish and lifecycle; no playbook execution in Scout or Carina core.**
3. **No GPLv3 Java in Keprix or Carina repos.**
4. **No second React Flow canvas in Carina.**
5. **Operator copy: playbook (not workflow, not KNIME workflow).**

---

## Verification checklist (pack complete)

| Check | Owner |
| --- | --- |
| Canvas roundtrip + run | Keprix 233 |
| 20+ connectors + studio deep link | Keprix 234 |
| Studio works in community edition | Keprix 235 |
| Scout receives publish + run events | Keprix 236 + Carina 03 |
| Aiva hire assigns template + run | Carina 02 + 05 |
| Carina opens studio authenticated | Carina 01 |
| Carina integrations proxy catalog | Carina 04 |
| n8n import shows warnings | Keprix 238 |
| Competitive note status updated | Docs |

---

## Archive order

When each prompt AC passes, archive to `prompts-archive/` (Keprix) or `prompts-library/archived/` (Carina). Update `PROMPT-IMPLEMENTATION-AUDIT.md` and master reference status table.

Keprix **233-238** are complete. Continue Carina `knime-adoption--01-05` from the Carina prompt queue when switching repositories.
