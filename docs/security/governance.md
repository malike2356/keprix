# Governance

Clinical and operational governance: Labyrinth Scout, evidence packs, and pack gate.

## Labyrinth Scout (`/settings/governance`)

Scout provides kill switches, audit trails, and policy enforcement for governed deployments.

### Requirements

- Scout Govern license from [labyrinthscout.com](https://labyrinthscout.com)
- API URL and key from provisioning email or Scout console
- keprix stores credentials encrypted; it does not sell Scout in-app

### Connect

1. Open **Settings > Governance**
2. Enter Scout API URL (default `https://api.labyrinthscout.com`) and API key
3. Test connection
4. Scout safety indicator appears in admin header when active

### Ungoverned mode

Without Scout, the header shows **Ungoverned**. Local policies and vault encryption still apply.

## Evidence packs (`/settings/governance/evidence-packs`)

Signed archives of clinical events for auditors:

- Date range and event type filters
- ZIP export with manifest
- Optional Scout upload

API: `/api/governance/evidence-packs/*`

## Pack gate (`/settings/pack-gate`)

Require clinical sign-off before new domain pack versions activate (DCB0160 / IEC 62304 style change control).

- Enable gate in settings
- Approver reviews pending installs at `/packs/{pack_id}/gate`
- Notifications sent to workspace inbox

## Tool ACL

Day-2 product and resource ACL: workspace **Admin > Tool ACL** (`/admin/tool-acl`).
See [Tool ACL](../features/tool-acl.md).

## Related

- [Scout integration](../integrations/scout.md)
- [Hub and domain packs](../features/hub-and-packs.md)
- [Security architecture](architecture.md)
