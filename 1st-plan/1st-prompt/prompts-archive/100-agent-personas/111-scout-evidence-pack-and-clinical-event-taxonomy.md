# keprix - Prompt 111: Scout Evidence Pack And Clinical Event Taxonomy

## Context

Read `46-scout-governance-bridge.md` thoroughly. This prompt extends prompt 46; do not re-implement what is already specified there. Prompt 30 covers: Scout enrollment, heartbeat, generic event reporting, policy receiver, kill switch, and the connector UI.

This prompt adds three specific capabilities on top of that foundation:

1. **Clinical event taxonomy**: a named, structured set of event types for compliance-sensitive workflows (clinical safety sign-off, compliance scans, hazard log management). These events have a richer schema than the generic `audit_log` events from Prompt 30.

2. **Evidence pack generation**: a structured, signed zip archive that can be presented to an external auditor or a Scout operator as proof of a compliance workflow execution. The pack is self-contained and verifiable without access to the keprix instance.

3. **Scout ingestion alignment**: the evidence pack format and event schema are designed to be ingested by the Labyrinth Scout audit console. This requires following the agreed Scout ingest schema rather than the internal keprix event format.

This is used by COMPASS (NHS clinical safety copilot) and any other domain pack that needs auditable, archivable evidence of AI-assisted compliance workflows.

---

## Clinical Event Taxonomy

All clinical events are sent to Scout via the `scout_event_queue` (Prompt 30) with `event_type` set to one of the values below. In addition to being forwarded to Scout, they are written to keprix's local audit log.

### Event Types

```python
CLINICAL_EVENT_TYPES = {
    # Hazard log lifecycle
    "hazard_log_created":          "A new hazard log entry was created",
    "hazard_log_updated":          "A hazard log entry was updated",
    "hazard_log_closed":           "A hazard log entry was closed/resolved",
    "hazard_log_exported":         "A hazard log was exported to PDF",

    # Review workflow (links to Prompt 117 review gateway)
    "cso_review_assigned":         "A clinical safety officer was assigned to review a hazard log",
    "cso_review_reminder_sent":    "A reminder was sent to a CSO for a pending review",
    "cso_review_approved":         "A CSO approved a hazard log",
    "cso_review_rejected":         "A CSO rejected a hazard log",
    "cso_review_change_requested": "A CSO requested changes to a hazard log",
    "cso_review_expired":          "A CSO review request expired without a decision",

    # Compliance scan lifecycle
    "compliance_scan_started":     "A compliance scan was triggered",
    "compliance_scan_complete":    "A compliance scan completed",
    "compliance_scan_failed":      "A compliance scan failed or errored",
    "compliance_finding_raised":   "A compliance issue or finding was identified",
    "compliance_finding_resolved": "A compliance finding was marked resolved",

    # Evidence pack
    "evidence_pack_generated":     "An evidence pack was assembled and stored",
    "evidence_pack_exported":      "An evidence pack was downloaded or sent to Scout",

    # GDPR (from Prompt 119)
    "gdpr_dsar_requested":         "A data subject access request was triggered",
    "gdpr_dsar_complete":          "A DSAR export was completed",
    "gdpr_erasure_complete":       "A right-to-erasure request was completed",
    "gdpr_consent_withdrawn":      "Consent was withdrawn for a processing purpose",
    "gdpr_retention_run":          "Automated retention enforcement ran",

    # Legal gate (from Prompt 130)
    "legal_acceptance_recorded":   "A user accepted the current legal policies",
    "legal_policy_published":      "A new legal policy version was published",
}
```

### Event Payload Schema

Every clinical event must include this envelope:

```python
class ClinicalEvent(BaseModel):
    event_id: str           # UUID, unique per event
    event_type: str         # from CLINICAL_EVENT_TYPES
    workspace_id: str
    instance_id: str        # keprix instance ID (from scout_config.instance_id)
    timestamp: str          # ISO 8601 UTC
    actor_type: str         # 'user', 'agent', 'playbook', 'system', 'external_reviewer'
    actor_id: str | None    # user UUID, agent name, playbook ID, or None for system
    subject_type: str | None  # what the event is about: 'hazard_log', 'review_request', 'scan', 'finding'
    subject_id: str | None    # ID of the subject entity
    summary: str            # one-sentence human-readable description
    detail: dict | None     # event-specific structured data (see per-event schemas below)
    severity: str           # 'info', 'notice', 'warning', 'critical'
    domain_pack: str | None # e.g. 'compass', 'legal-review'; None for general keprix events
    signature: str          # HMAC-SHA256 of canonical JSON of all above fields (for evidence pack verification)
```

Canonical JSON for signing: fields sorted alphabetically, `signature` field omitted, serialised with `separators=(',', ':')`.

### Per-Event Detail Schemas

Selected examples:

```python
# cso_review_approved / rejected / change_requested
{
    "review_request_id": "<uuid>",
    "reviewer_name": "<name>",
    "reviewer_email_hash": "<sha256 of reviewer email>",
    "decision": "approve" | "reject" | "request_change",
    "note_length": 142,         # length of note, not its content
    "token_id": "<uuid>",
    "artifact_title": "<title>",
}

# compliance_scan_complete
{
    "scan_id": "<uuid>",
    "scan_type": "dcb0129" | "dcb0160" | "iso27001" | "custom",
    "findings_count": 3,
    "critical_count": 0,
    "warning_count": 2,
    "pass_count": 47,
    "duration_seconds": 18,
}

# compliance_finding_raised
{
    "finding_id": "<uuid>",
    "scan_id": "<uuid>",
    "standard": "DCB0129",
    "clause": "4.3",
    "severity": "warning",
    "description": "<first 200 chars of finding description>",
}

# evidence_pack_generated
{
    "pack_id": "<uuid>",
    "pack_sha256": "<sha256 of zip file>",
    "event_count": 47,
    "date_from": "<iso8601>",
    "date_to": "<iso8601>",
    "included_types": ["cso_review_approved", "compliance_scan_complete", ...],
}
```

---

## Emitting Clinical Events

Add a `emit_clinical_event` helper that wraps the Scout event queue from Prompt 30 and also writes to the local audit log:

```python
# keprix/backend/scout/clinical_events.py

async def emit_clinical_event(
    event_type: str,
    workspace_id: str,
    actor_type: str,
    summary: str,
    actor_id: str | None = None,
    subject_type: str | None = None,
    subject_id: str | None = None,
    detail: dict | None = None,
    severity: str = "info",
    domain_pack: str | None = None,
) -> str:
    """
    Builds, signs, and dispatches a clinical event.
    Returns the event_id.
    """
    event = ClinicalEvent(
        event_id=str(uuid4()),
        event_type=event_type,
        workspace_id=workspace_id,
        instance_id=await scout_config.get_instance_id(),
        timestamp=datetime.utcnow().isoformat() + "Z",
        actor_type=actor_type,
        actor_id=actor_id,
        subject_type=subject_type,
        subject_id=subject_id,
        summary=summary,
        detail=detail,
        severity=severity,
        domain_pack=domain_pack,
        signature="",   # filled in below
    )
    event.signature = sign_event(event, hmac_secret=vault.get("CLINICAL_EVENT_HMAC_SECRET"))

    # Write to local audit log
    await audit_log.write(event.event_type, event.summary, metadata=event.dict())

    # Queue for Scout if connected
    if await scout_config.is_enabled():
        await scout_event_queue.enqueue(event_type=event.event_type, payload=event.dict())

    return event.event_id
```

Usage from any module:

```python
await emit_clinical_event(
    event_type="cso_review_approved",
    workspace_id=workspace_id,
    actor_type="external_reviewer",
    actor_id=None,
    subject_type="review_request",
    subject_id=str(review_request.id),
    summary=f"CSO {reviewer_name} approved hazard log '{title}'",
    detail={"review_request_id": str(review_request.id), ...},
    domain_pack="compass",
)
```

Modules that must call `emit_clinical_event`:
- Review gateway (Prompt 117): on review created, decided, expired.
- GDPR module (Prompt 119): on DSAR, erasure, retention run, consent withdrawn.
- Legal gate (Prompt 130): on acceptance recorded, policy published.
- Domain packs (Prompt 30): on compliance scan events.

---

## Evidence Pack Generation

An evidence pack is a signed zip file that proves to an external auditor that a compliance workflow ran correctly and produced documented outcomes.

### File Structure Inside the Zip

```
evidence-pack-{pack_id}/
    manifest.json           - pack metadata and verification instructions
    events/
        {event_id}.json     - one file per clinical event included in the pack
    documents/
        {filename}.pdf      - any PDF exports linked to events in the pack (e.g. hazard log PDFs)
    audit_extract.csv       - local audit log extract for the covered period
    VERIFY.txt              - human-readable instructions for verifying signatures
```

### `manifest.json` Schema

```json
{
  "pack_id": "<uuid>",
  "pack_version": "1.0",
  "generated_at": "<iso8601>",
  "workspace_id": "<uuid>",
  "instance_id": "<uuid>",
  "keprix_version": "<semver>",
  "date_from": "<iso8601>",
  "date_to": "<iso8601>",
  "event_count": 47,
  "document_count": 3,
  "included_event_types": ["cso_review_approved", "compliance_scan_complete"],
  "events_sha256": {
    "{event_id}": "<sha256 of events/{event_id}.json>"
  },
  "documents_sha256": {
    "{filename}": "<sha256 of documents/{filename}>"
  },
  "manifest_signature": "<HMAC-SHA256 of canonical JSON of all above fields>"
}
```

The `manifest_signature` signs the entire manifest (excluding itself) using the `CLINICAL_EVENT_HMAC_SECRET` from vault. This allows an auditor who has the public HMAC key to verify the pack has not been tampered with.

`VERIFY.txt` explains:
1. How to compute the HMAC of each event JSON file and compare to the `events_sha256` map.
2. How to compute the HMAC of the manifest (excluding `manifest_signature`) and compare to `manifest_signature`.
3. Where to get the HMAC key (from the operator who generated the pack; they must disclose it for audit purposes).

### Pack Generation API

```
POST /api/evidence-pack/generate
     Requires workspace auth + admin role.
     Body: {
       date_from: iso8601,
       date_to: iso8601,
       event_types?: string[],     -- filter; omit for all clinical events
       include_documents: bool,    -- whether to bundle linked PDF exports
       domain_pack?: string        -- filter by domain pack (e.g. 'compass')
     }
     Returns: { pack_id, status: 'generating' }

GET  /api/evidence-pack/{pack_id}
     Returns: { status, download_url?, event_count, document_count, generated_at }

GET  /api/evidence-pack/{pack_id}/download
     Returns: zip file download

POST /api/evidence-pack/{pack_id}/send-to-scout
     If Scout is connected, uploads the pack to the Scout evidence store.
     Returns: { scout_submission_id }

GET  /api/evidence-pack
     Returns: list of generated packs for this workspace
```

### Pack Generation Implementation

```python
async def generate_evidence_pack(
    workspace_id: str,
    date_from: datetime,
    date_to: datetime,
    event_types: list[str] | None = None,
    include_documents: bool = True,
    domain_pack: str | None = None,
) -> str:
    pack_id = str(uuid4())

    # 1. Collect events from audit_log where event_type is in CLINICAL_EVENT_TYPES
    events = await collect_clinical_events(workspace_id, date_from, date_to, event_types, domain_pack)

    # 2. Collect linked documents (PDFs created during the covered period)
    documents = []
    if include_documents:
        documents = await collect_linked_documents(workspace_id, events)

    # 3. Extract local audit log as CSV
    audit_csv = await audit_log.export_csv(workspace_id, date_from, date_to)

    # 4. Assemble zip in memory
    zip_buffer = build_evidence_zip(pack_id, events, documents, audit_csv)

    # 5. Store zip in workspace file store
    file_id = await file_store.save(
        workspace_id=workspace_id,
        path=f"evidence-packs/{pack_id}.zip",
        content=zip_buffer,
        content_type="application/zip",
    )

    # 6. Emit evidence_pack_generated event
    await emit_clinical_event(
        event_type="evidence_pack_generated",
        workspace_id=workspace_id,
        actor_type="system",
        summary=f"Evidence pack generated for period {date_from.date()} to {date_to.date()}",
        detail={"pack_id": pack_id, "event_count": len(events), ...},
    )

    return pack_id
```

---

## Scout Upload Integration

If Scout is connected and the operator sends a pack to Scout:

```
POST {scout_url}/api/v1/evidence-packs
Authorization: Bearer {scout_api_key}
Content-Type: application/zip
X-Pack-ID: {pack_id}
X-Workspace-ID: {workspace_id}
X-Instance-ID: {instance_id}
X-Manifest-Signature: {manifest_signature}
Body: zip file bytes
```

On success, Scout returns:
```json
{ "submission_id": "<uuid>", "scout_pack_url": "<url>", "accepted_at": "<iso8601>" }
```

Store `scout_submission_id` and `scout_pack_url` against the pack record. Show in the pack detail UI with a link to open in Scout.

If Scout is not connected, `send-to-scout` returns HTTP 409: "Scout is not connected. Configure Scout in settings > governance to enable this feature."

---

## Acceptance Criteria

- `emit_clinical_event` with a valid `event_type` writes to local audit log and queues to Scout if Scout is enabled.
- An event with an invalid `event_type` (not in `CLINICAL_EVENT_TYPES`) raises a `ValueError`; it is not silently queued.
- Event JSON files in the evidence pack each have a valid HMAC signature verifiable with the `CLINICAL_EVENT_HMAC_SECRET`.
- `manifest.json` sha256 entries match the actual sha256 of each event file in the zip.
- `manifest_signature` verifies correctly against the manifest fields.
- A pack generated for a date range containing 20 events produces a zip with exactly 20 event JSON files.
- `send-to-scout` returns HTTP 409 when Scout is not configured.
- `send-to-scout` with Scout connected POSTs the zip to Scout and returns the submission ID.
- GDPR and legal acceptance events from Prompts 109 and 110 appear in packs that include those event types.
- `GET /api/evidence-pack` returns the list of previously generated packs including their status and event counts.
