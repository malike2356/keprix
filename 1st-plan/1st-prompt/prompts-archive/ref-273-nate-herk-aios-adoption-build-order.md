# Nate Herk AIOS adoption build order (Keprix 274-279)

**Master reference:** `273-nate-herk-aios-adoption-master-reference.md`  
**Transcript:** `planning/competitor-research/youtube-bCljOfCH8Ms-transcript.txt`

---

## Critical path

```text
276 (onboard) --> context/ files for 274 scoring

274 (four-cs audit) --> 275 (level-up)

277 (connections) --> 279 (google workspace) + 265 day-2 step

278 (hot cache) --> 258 vault template (parallel OK)

264 / 265 amendments ship with 276 + 274
```

---

## Prompt order

| Order | Prompt | Title | Depends on | Parallel OK? |
| --- | --- | --- | --- | --- |
| 1 | **276** | Onboard interview skill | **258** stub OK | - |
| 2 | **274** | Four C's OS maturity audit | **276** context files | Yes with 277 |
| 2b | **277** | Connections tier matrix | **265** stub OK | Yes with 274 |
| 3 | **275** | Level-up remediation skill | **274** | - |
| 4 | **278** | Hot cache vault layer | **258**, `llm-wiki` | Yes with 279 |
| 4b | **279** | Google Workspace connector | **277** | Yes with 278 |

**Amend after 276 + 274:** update **264** pack manifest; update **265** steps.

---

## Minimum viable Nate parity (demo)

Ship **276 + 274 + 277**:

- New operator runs onboard interview
- Maturity audit scores Context low, Connections gap on tier-1
- Day-2 wizard picks Google Workspace as first wire-up target

Add **279** for connections demo; **275** for remediation story; **278** for EA token savings.

---

## Parallel with other packs

| Track | Relationship |
| --- | --- |
| Agentic OS **256-265** | Nate pack extends; do not duplicate 256 workflow audit |
| Chase **267-272** | **267** feeds wiki; **272** optional Obsidian |
| KNIME **234** | **279** registers in connector catalog |

---

## Archive order

Archive **274-279** to `prompts-archive/` when AC pass. Update `PROMPT-IMPLEMENTATION-AUDIT.md`, master reference status table, and `nate-herk-aios-adoption.md`.
