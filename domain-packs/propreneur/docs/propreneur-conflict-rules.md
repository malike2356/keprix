# Propreneur Aiva conflict rules

## Rule

Aiva writes to Propreneur must include the `resource_version` (or equivalent ETag / `If-Match`) read from Propreneur.

## On HTTP 409

1. Do not last-write-wins.
2. Fetch the latest record from Propreneur.
3. Show a meaningful field-level diff between the attempted write and the current record.
4. Ask the user for a new decision when automatic merge is unsafe.
5. Re-submit with the fresh version after approval.

## Diff path (Aiva)

Suggested operator / agent path:

1. `GET` current resource.
2. Compare planned patch vs current values.
3. Present: tenant, resource id, version before, version now, conflicting fields.
4. Create a new pending approval (or bridge proposal) bound to a new digest.
5. Invalidate any previous approval digest for the stale version.

## Not allowed

- Unrestricted bidirectional database replication
- Silent overwrite of concurrent human edits
- Fabricating success after a 409
