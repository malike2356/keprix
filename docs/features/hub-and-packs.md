# Hub and domain packs

Install, manage, and gate domain-specific capability packs.

## Skills Hub (`/skills`)

Browse installed skills and plugins. Skills extend agent tools and slash commands.

See [Skills and plugins](skills.md).

## Hub (`/hub`)

Catalog of available packs with install actions. Packs may include:

- Agent personas
- Clinical or domain workflows
- Tool and skill bundles
- YAML playbooks

## Domain packs (`/domain-packs`)

Domain-specific pack versions with optional **pack gate** sign-off before activation.

### Pack gate

When enabled (`/settings/pack-gate`):

1. Pack installs but stays inactive
2. Approver reviews at `/packs/{pack_id}/gate`
3. Sign-off recorded; version activates

See [Governance](../security/governance.md).

## API

- `/api/hub/*` catalog and install
- `/api/domain-packs/*` versions and gate

## Related

- [Governance](../security/governance.md)
- [Skills](skills.md)
- [Playbooks](playbooks.md)
