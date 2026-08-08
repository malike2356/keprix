# Prompt KUS-07: Context, memory, files, privacy, and retention

**Status: COMPLETED 2026-08-08**
**Depends on:** KUS-01, KUS-03 through KUS-06
**Blocks:** KUS-08 through KUS-12

## What was built

- Namespaced memory with ephemeral default + DSAR export
- File ingest bounds; deletion receipts; cross-tenant isolation

## Goal

Let projects provide useful context and memory without bulk data access, namespace
leakage, permanent retention, unsafe files or model-provider over-sharing.

## Must-haves

1. Context slice contract declares key, purpose, schema, product operation or event,
   sensitivity, TTL, maximum records/bytes, required grants, allowed nodes and
   redaction. Fetch lazily and only for an invoked capability.
2. Namespace includes project, deployment, environment, tenant, actor/subject when
   applicable, pack, source and retention class. All search/index/delete paths use it.
3. Memory modes: disabled, ephemeral session, project facts, subject memory and
   shared approved knowledge. Default universal quickstart is ephemeral.
4. Writes require source/provenance, source version, observed/generated class,
   confidence/verification, purpose, expiry and deletion key. Generated inference
   is never promoted to verified project truth automatically.
5. Project deletion/correction/retention events remove or update indexes, cache,
   artifacts, summaries and pending work with completion receipt.
6. File ingestion uses explicit content type, size/count/decompression/page limits,
   malware/archive checks, encrypted-file handling, sandbox conversion and no macro/
   formula execution. Preserve content hash and source metadata.
7. Files and context are untrusted for prompt injection. Retrieval separates data
   from instruction and enforces citations/allowed tool paths.
8. Provider routing considers sensitivity, residency, data-retention terms and
   project policy. Sensitive content cannot fall back to an ineligible cloud model.
9. Logs/traces/metrics avoid content by default. Debug content capture is temporary,
   explicit, access-controlled, redacted and disabled in public quickstart.
10. DSAR/export is project/tenant scoped and excludes internal secrets or other
    projects. Backup/restore and deprovision preserve deletion obligations.

## Acceptance

- [x] Cross-project/tenant memory retrieval fails across every mode
- [x] Ephemeral mode leaves no durable content after expiry
- [x] Malicious file cannot execute or widen tools
- [x] Retention/deletion propagation has auditable completion
