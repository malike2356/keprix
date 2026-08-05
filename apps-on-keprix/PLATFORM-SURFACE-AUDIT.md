# Platform Surface Audit: Cross-Product Foundation Map

**Purpose:** Tells the keprix foundation build which prompts are load-bearing for which product, so the build order targets real consumer needs rather than theoretical completeness.

**Per-product detail:** `petraclus/keprix-SURFACE-AUDIT.md`, `abbis/keprix-SURFACE-AUDIT.md`, `NHS/keprix-SURFACE-AUDIT.md`, `fleetz/keprix-SURFACE-AUDIT.md`.

---

## Product Summary

| Product | keprix role | When keprix needed | Complexity of integration |
|---|---|---|---|
| **Petraclus** | Text reasoning sidecar; 4 fixed completion tasks | From day one of Petraclus v1 | Low: HTTP completions only |
| **AbbiS** | Domain AI assistants; RAG over borehole corpus | From day one of AbbiS v1 | Medium: RAG + domain pack + playbooks |
| **Fleetz** | Fleet intelligence (anomaly explanation, reports) | v2 only; MVP ships without keprix | Low when it arrives |
| **COMPASS** | Full compliance inference engine; entire workflow | From day one of COMPASS v1 | High: full stack including 86-92 |

---

## Cross-Product Load Table

Each row is a foundation prompt. Columns show what each product needs it for.

| Prompt | Petraclus v1 | AbbiS v1 | COMPASS v1 | Fleetz v2 | Priority |
|---|---|---|---|---|---|
| **00 project setup** | Required | Required | Required | Required | P0 |
| **01 developer identity** | Required | Required | Required | Required | P0 |
| **02 security foundation** | Required | Required | Required | Required | P0 |
| **03 agent engine** | Required | Required | Required | Required | P0 |
| **04 model routing** | Required | Required | Required | Required | P0 |
| **05 tools and terminal** | Not needed v1 | Required (file tools, web search, python calc) | Required (read_file, web_search, python AST) | Required v2 | P0 for AbbiS/COMPASS |
| **06 memory and RAG** | Not needed v1 | CRITICAL (borehole corpus, project memory) | CRITICAL (NHS standards corpus, hazard log memory) | Not needed v1 | P0 for AbbiS/COMPASS |
| **07 skills and plugins** | Not needed v1 | Required (pack loader for borehole-africa) | Required (pack loader for compass-compliance) | Not needed | P0 for AbbiS/COMPASS |
| **08 vault** | Required | Required | Required | Required | P0 |
| **09 workspace documents** | Not needed v1 | Required (soil report file store) | Required (uploaded PRD/arch/spec files) | Not needed v1 | P1 for AbbiS/COMPASS |
| **10 email integration** | Not needed | Not needed | Not needed | Not needed | Defer |
| **11 messaging gateway** | Not needed | Not needed | Not needed | Not needed | Defer |
| **12 deep research** | Not needed v1 | Not needed v1 | Not needed v1 | Not needed | Defer |
| **13 cron** | Not needed v1 | Not needed v1 | Not needed (playbook handles timing) | Required v2 (weekly report trigger) | Defer |
| **14 self-configuration** | Not needed v1 | Not needed v1 | Not needed v1 | Not needed | Defer |
| **15 MCP/ACP integrations** | Not needed v1 | Not needed v1 | Not needed v1 | Not needed | Defer |
| **16 REST API and health** | CRITICAL (Petraclus calls this directly) | Required | Required | Required v2 | P0 |
| **17 OpenAI-compatible API** | Not needed | Not needed | Not needed | Not needed | Defer |
| **18 mobile apps** | Not needed | Not needed | Not needed | Not needed | Defer |
| **19 Python+TS SDK** | Beneficial (SDK wraps HTTP) | Beneficial | Not needed | Not needed | P1 for Petraclus |
| **20 agent hardening** | Required (input from Petraclus tool outputs) | Required | Required | Not needed | P0 |
| **30 governance reporting** | Not needed v1 | Not needed v1 | Not needed v1 | Not needed | Defer |
| **34 notifications inbox** | Not needed v1 | Not needed v1 | Required (internal alerts when CSO decides) | Not needed | P1 for COMPASS |
| **38 domain pack factory** | Not needed v1 | CRITICAL (builds borehole-africa pack) | CRITICAL (builds compass-compliance pack) | Not needed | P0 for AbbiS/COMPASS |
| **46 Scout bridge** | Optional (Pro/Team) | Optional | Required (evidence packs go to Scout) | Not needed | P2 |
| **64 playbook runtime** | Not needed v1 | Required (quote + compliance playbooks) | CRITICAL (12-step durable compliance scan) | Not needed | P0 for AbbiS/COMPASS |
| **67 analytics workspace** | Not needed | Not needed | Not needed | Required v2 | Defer |
| **86 review gateway** | Not needed | Not needed | CRITICAL (the CSO marketplace is this) | Not needed | P0 for COMPASS |
| **87 PDF export** | Not needed v1 | Required (quotes, reports) | Required (Hazard Log PDFs) | Required v2 | P1 |
| **88 GDPR** | Not needed v1 | Not needed v1 | Required (NHS procurement requirement) | Not needed | P1 for COMPASS |
| **89 legal gate** | Not needed v1 | Not needed v1 | Required (DPA acceptance before doc processing) | Not needed | P1 for COMPASS |
| **90 evidence packs** | Not needed | Not needed | Required (audit trail for NHS sign-off) | Not needed | P0 for COMPASS |
| **91 clinical pack gate** | Not needed | Not needed | Required (DCB0160 change control) | Not needed | P1 for COMPASS |
| **92 outbound notify** | Not needed v1 | Required (quote emails to clients) | Required (CSO email dispatch with review link) | Required v2 | P1 for AbbiS/COMPASS |

---

## Build Priority Derived From Consumer Needs

### P0: Must be stable before ANY product ships

These 9 prompts unblock Petraclus v1, which is the fastest path to a live keprix consumer:

```
00, 01, 02, 03, 04, 08, 16, 19, 20
```

Once these are solid, Petraclus can ship. That validates the runtime before AbbiS or COMPASS add complexity.

### P0: Must be stable before AbbiS ships

These additional prompts are needed on top of the core 9:

```
05, 06, 07, 09, 38, 64, 87, 92
```

Of these, **06 (memory and RAG)** and **38 (domain pack factory)** are the quality gates. If they are slow, inaccurate, or brittle, the entire AbbiS product fails. These deserve the most careful implementation and the most test coverage.

### P0: Must be stable before COMPASS ships

On top of everything AbbiS needs, COMPASS additionally requires:

```
34, 86, 88, 89, 90, 91, 92
```

Of these, **86 (review gateway)** and **90 (evidence packs)** are the strategic moat. Without the CSO sign-off flow, COMPASS is just another document generator. With it, COMPASS has something no competitor can trivially copy.

### P2: Optional connector (Petraclus Pro/Team)

```
46 (Scout bridge)
```

Deferred to after Petraclus community tier ships. Not needed to validate the keprix runtime.

### Defer: Not needed by any v1 consumer

```
10, 11, 12, 13, 14, 15, 17, 18, 30, 31, 32, 33, 35, 36, 37, 39, 40, 41, 42, 43, 44, 45, 47-63, 65, 66, 68-85
```

These are real features (Opportunity Engine, marketing site, mutation engine, mobile, community, etc.) but no v1 consumer is blocked on them. Build after the consumer-critical path is stable.

---

## Recommended Foundation Build Sequence

Based purely on consumer dependency, not theoretical completeness:

```
Wave 1 (Petraclus unblocked):
  03 -> 04 -> 02 -> 20 -> 08 -> 16 -> 00 + 01 (setup)
  Test: Petraclus can call /api/health and get a completion response.

Wave 2 (SDK and tooling for AbbiS):
  05 (file tools, web search, python tool)
  09 (workspace documents and file store)
  19 (Python + TypeScript SDK)
  Test: Petraclus SDK works. AbbiS can upload a soil report and retrieve it.

Wave 3 (RAG and domain packs - the AbbiS moat):
  06 (memory and RAG with pgvector, hybrid search)
  07 (skill loader with hot reload)
  38 (domain pack factory: ingest corpus, build pack, serve)
  Test: AbbiS borehole-africa pack loads. RAG query returns a grounded answer.

Wave 4 (Playbooks and outputs):
  64 (durable playbook runtime with pause and resume)
  87 (PDF export)
  92 (outbound notify: SMTP + webhook)
  Test: Quote generation playbook runs, pauses for input, resumes, generates PDF, sends email.

Wave 5 (COMPASS governance stack):
  34 (notifications inbox - internal alerts)
  88 (GDPR infrastructure)
  89 (legal acceptance gate)
  86 (external human review gateway - the CSO marketplace)
  90 (Scout evidence pack and clinical event taxonomy)
  91 (clinical pack gate)
  Test: Full COMPASS scan playbook: code diff in, CSO email out, CSO approves,
        evidence pack generated, Hazard Log PDF downloaded.

Wave 6 (Scout connector - Petraclus Pro/Team):
  46 (Scout bridge)
```

---

## Key Insights From This Audit

**Petraclus is the fastest first consumer by a large margin.** It needs 7 prompts. Everything else can be deferred. Shipping Petraclus validates the runtime before complexity is added.

**AbbiS and COMPASS share a large foundation.** Prompts 05, 06, 07, 09, 38, 64, 87, 92 are needed by both. Build them once, test them against AbbiS (simpler domain), then layer COMPASS on top.

**RAG quality is the highest-stakes implementation decision.** Both AbbiS and COMPASS fail if Prompt 06 is slow or inaccurate. Hybrid search (vector + keyword) is required for both; vector-only search would miss location-specific queries in AbbiS ("yield near Bolgatanga") and clause-specific queries in COMPASS ("DCB0129 clause 4.3").

**Prompt 86 (review gateway) is COMPASS's single biggest differentiator.** No other NHS compliance tool has a machine-enforced CSO sign-off flow with a digital audit record. Everything else in COMPASS (code scanning, hazard inference, PDF generation) can be approximated by competitors. The review gateway is architecturally unique.

**Fleetz places zero pressure on the build timeline.** It needs keprix only in v2, and only for analytics (Prompt 67) and report generation (87, 92). Both will be built before Fleetz v2 is started.
