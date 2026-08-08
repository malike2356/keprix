# keprix - Prompt 112: Clinical Pack Gate

## Context

Read `superseded-07-skills-and-plugins.md` or inspect
`src/keprix/skills/` and `src/keprix/plugins/` thoroughly. This prompt extends the skill and
plugin system from the Hermes clone; it does not replace it. That foundation covers: skill
loader, plugin registry, hot reload, community pack schema, and pack installation.

This prompt adds a mandatory sign-off gate that sits between pack installation and pack activation in safety-sensitive deployments. The gate is not active by default. It is enabled per workspace via configuration, and once enabled, it applies to every skill pack version change in that workspace.

The motivation is regulatory: in certain regulated industries (clinical software, financial services, legal), deploying a new version of an automated decision-support component without a documented change approval record is a non-compliance event. The gate provides that record.

Two concepts from standards this addresses:
- **DCB0160** (NHS clinical risk management for deployed health IT): change control requires that every update to software in a clinical context is assessed, approved by a responsible person, and documented.
- **ISO 9001 / IEC 62304** software change control: changes must be reviewed and authorised before deployment.

The gate is implemented entirely within keprix. It does not require Scout or any external service, though it emits clinical events to Scout if Scout is connected (Prompt 131).

---

## Design Principles

The gate does not know what the pack does or whether the change is safe. It enforces a process: a responsible person (the configured approver for that workspace) must acknowledge the changelog and declare that they are accepting responsibility for activating the new version. keprix's role is to record that declaration reliably.

The gate does not block installation. Packs can be downloaded and stored in the pack registry at any time. The gate blocks activation: the pack version is marked `installed` but cannot be loaded by the agent runtime until the gate is cleared.

Rollback is always available: the previously active signed version can be restored in a single step, and that rollback also requires a sign-off record.

---

## File Structure

```
keprix/backend/pack_gate/
    __init__.py
    models.py           - DB models for gate records and sign-off log
    gate.py             - gate enforcement logic (called by skill loader from Prompt 07)
    routes.py           - API for gate management
    schemas.py          - Pydantic schemas
    notifications.py    - notifies configured approver via workspace inbox and email

keprix/tests/pack_gate/
    test_gate.py
    test_routes.py

keprix/ui/web/src/app/(workspace)/settings/pack-gate/
    page.tsx            - pack gate settings and pending approvals list

keprix/ui/web/src/app/(workspace)/packs/[pack_id]/gate/
    page.tsx            - sign-off page for a specific pending version
```

---

## Database

```sql
CREATE TABLE pack_gate_config (
    workspace_id UUID PRIMARY KEY,
    enabled BOOLEAN NOT NULL DEFAULT FALSE,
    approver_user_id UUID,
    -- null if not yet configured; gate cannot be enabled without an approver set
    approver_email TEXT,
    -- snapshot of approver email at config time; used for notifications
    notify_on_install BOOLEAN NOT NULL DEFAULT TRUE,
    -- send inbox/email alert when a new version is installed and awaiting sign-off
    require_changelog BOOLEAN NOT NULL DEFAULT TRUE,
    -- if true, pack must supply a CHANGELOG entry for the version; reject if missing
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE pack_gate_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL,
    pack_id TEXT NOT NULL,
    -- pack identifier, e.g. 'compass-compliance', 'legal-review'
    from_version TEXT,
    -- null for first install
    to_version TEXT NOT NULL,
    changelog_text TEXT,
    -- extracted from pack manifest CHANGELOG section
    status TEXT NOT NULL DEFAULT 'pending',
    -- 'pending', 'approved', 'rejected', 'rolled_back', 'cancelled'
    signed_off_by_user_id UUID,
    signed_off_at TIMESTAMPTZ,
    sign_off_note TEXT,
    requested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    requested_by_user_id UUID,
    -- user who triggered the install; may differ from approver
    UNIQUE (workspace_id, pack_id, to_version)
);

CREATE TABLE pack_gate_rollback_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL,
    pack_id TEXT NOT NULL,
    rolled_back_from_version TEXT NOT NULL,
    rolled_back_to_version TEXT NOT NULL,
    reason TEXT,
    initiated_by_user_id UUID,
    initiated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    gate_record_id UUID REFERENCES pack_gate_records(id)
);

CREATE INDEX ON pack_gate_records(workspace_id, status);
CREATE INDEX ON pack_gate_records(workspace_id, pack_id);
```

---

## Integration With Skill Loader (Prompt 07)

The skill loader in Prompt 07 has an `activate(pack_id, version)` step that loads a pack into the runtime. Insert the gate check at the start of that step:

```python
# In the skill loader (keprix/backend/skills/loader.py), extend activate():

async def activate(self, pack_id: str, version: str, workspace_id: str) -> None:
    if await pack_gate.is_gate_enabled(workspace_id):
        gate_record = await pack_gate.get_gate_record(workspace_id, pack_id, version)
        if gate_record is None:
            # No gate record exists: installation happened without going through the gate
            # Create one retroactively and block activation
            await pack_gate.create_gate_record(workspace_id, pack_id, version, from_version=await self.current_version(pack_id))
            raise PackGateRequired(pack_id=pack_id, version=version, workspace_id=workspace_id)
        if gate_record.status != "approved":
            raise PackGateRequired(pack_id=pack_id, version=version, workspace_id=workspace_id)

    # Gate cleared or not enabled; proceed with normal activation
    await self._load_pack_runtime(pack_id, version)
```

`PackGateRequired` is caught by the pack install API endpoint, which returns HTTP 202 (Accepted but not active) rather than HTTP 200. The response body includes `{ "gate_required": true, "gate_record_id": "...", "sign_off_url": "..." }`.

---

## Pack Manifest Changelog Requirement

When `require_changelog` is true in the workspace gate config, the pack loader must check that the pack manifest includes a `changelog` field for the version being installed:

```json
{
  "pack_id": "compass-compliance",
  "version": "1.4.0",
  "name": "COMPASS Compliance",
  "changelog": {
    "1.4.0": "Updated DCB0129 Hazard Log schema to v2. Added automated severity scoring. Fixed edge case in hazard ID generation."
  }
}
```

If `require_changelog` is true and the changelog field is missing or empty for the target version, the install is rejected with HTTP 422: "Pack manifest missing changelog for version {version}. This workspace requires a changelog entry for all pack updates."

The changelog text is stored in `pack_gate_records.changelog_text` so the approver sees it on the sign-off page.

---

## Approval Flow

### Step 1: Pack installed (not yet active)

Pack is downloaded and stored in the registry. `pack_gate_records` row created with `status = 'pending'`.

If `notify_on_install` is true:
- Send a workspace inbox notification (Prompt 24): "A new version of '{pack_name}' (v{to_version}) is awaiting your approval to activate."
- Send an email to `approver_email` via the outbound notify-external mechanism (Prompt 133).

### Step 2: Approver reviews and signs off

Approver navigates to `/packs/{pack_id}/gate` or follows the email link.

The sign-off page shows:
- Pack name and version.
- From version (currently active).
- Changelog text.
- A declaration text: "By clicking 'Approve and activate', I confirm that I have reviewed the changes described above and accept responsibility for activating version {to_version} of {pack_name} in this workspace."
- Optional note field.
- Two buttons: "Approve and activate" and "Reject".

On submit:
- Record `signed_off_by_user_id`, `signed_off_at`, `sign_off_note`, and `status = 'approved'` or `'rejected'`.
- If approved: call `skill_loader.activate(pack_id, to_version, workspace_id)` immediately.
- Emit `cso_review_approved` or equivalent clinical event via Prompt 131 (`emit_clinical_event`).

### Step 3: Rollback

Any workspace admin can trigger a rollback via the UI or API:

```
POST /api/pack-gate/{workspace_id}/packs/{pack_id}/rollback
Body: { reason }
```

Rollback:
1. Identifies the previously approved version (last `approved` gate record before the current one).
2. Creates a new `pack_gate_rollback_log` entry.
3. Calls `skill_loader.activate(pack_id, previous_version, workspace_id)` - rollback does NOT require a new gate sign-off, but it IS logged.
4. Emits a `compliance_finding_raised` clinical event with severity `warning`: "Pack {pack_id} was rolled back from {current} to {previous}."

---

## API Endpoints

```
GET  /api/pack-gate/config
     Returns: { enabled, approver_user_id, notify_on_install, require_changelog }

PUT  /api/pack-gate/config
     Body: { enabled, approver_user_id, notify_on_install, require_changelog }
     Cannot enable without approver_user_id set.

GET  /api/pack-gate/records
     Query: status, pack_id
     Returns: paginated list of gate records for this workspace

GET  /api/pack-gate/records/{id}
     Returns: full gate record

POST /api/pack-gate/records/{id}/approve
     Body: { note? }
     Approves and activates the pending version.
     Must be called by the configured approver or a super-admin.

POST /api/pack-gate/records/{id}/reject
     Body: { note }
     Rejects the pending version. Pack remains installed but not active.

POST /api/pack-gate/packs/{pack_id}/rollback
     Body: { reason }
     Rolls back to last approved version.

GET  /api/pack-gate/packs/{pack_id}/history
     Returns: full gate history for this pack in this workspace
```

---

## Sign-off Page UI (`/packs/{pack_id}/gate`)

This page is only accessible to authenticated workspace users. It is not a public page (unlike the review gateway in Prompt 117).

If the user is not the configured approver and not a super-admin: show the changelog and status, but action buttons are disabled with "Only the configured approver can sign off on pack changes."

If the gate record status is already `approved` or `rejected`: show a read-only summary.

---

## Pack Gate Settings UI (`/settings/pack-gate`)

- Toggle: "Require sign-off before activating new pack versions" (enable/disable the gate).
- Approver selector: search for workspace users by name or email.
- Checkboxes: "Notify on install" and "Require changelog".
- Table: all pending gate records, with links to sign-off pages.
- Table: recent approval and rejection history.
- Warning shown when gate is enabled but no approver is set: "Set an approver to complete gate configuration."

---

## Acceptance Criteria

- When the gate is enabled, installing a new pack version sets it to `installed` but `not active`. The install API response includes `gate_required: true`.
- The approver receives a workspace inbox notification when a version is pending.
- Navigating to the sign-off page shows the changelog text from the pack manifest.
- Clicking "Approve and activate" sets the gate record to `approved` and activates the pack in the skill loader.
- Clicking "Reject" sets the record to `rejected`. The pack remains not active.
- A non-approver user sees the sign-off page but cannot submit the form.
- Rollback deactivates the current version and activates the prior approved version in a single step.
- The rollback is logged to `pack_gate_rollback_log` and emits a clinical event.
- When `require_changelog` is true and the pack manifest has no changelog entry for the version, the install is rejected with HTTP 422.
- When the gate is disabled, packs install and activate immediately (existing Prompt 07 behaviour unchanged).
- Gate records are visible in the pack gate history UI with correct status and sign-off timestamps.
