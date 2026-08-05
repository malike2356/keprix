# keprix - Prompt 36: Hub, Marketplace, Packs, And Template Distribution

## Purpose

Build a Carina Hub and marketplace system for distributing skill packs, app templates, domain packs, plugins, prompts, UI templates, workflows, and connectors.

keprix should make it easy for the community to build on the core workspace while keeping installation safe, auditable, and reversible.

## Scope

Implement:

- Local pack registry.
- Remote hub registry.
- Pack manifest format.
- Pack signing and verification.
- Install, update, disable, and remove flows.
- App template gallery.
- Domain knowledge pack gallery.
- Connector gallery.
- Review and trust metadata.
- Dependency checks.
- Safety scan before install.
- Versioned pack releases.

## Output Paths

```text
keprix/backend/hub/
  __init__.py
  registry.py
  manifests.py
  installer.py
  verifier.py
  scanner.py
  updates.py
  rollback.py
  schemas.py

keprix/ui/web/hub/
keprix/packages/
  packs/
  templates/
  connectors/

keprix/docs/hub/
keprix/tests/hub/
```

## Pack Types

Support:

- Skill pack.
- Tool pack.
- Domain knowledge pack.
- App template.
- UI template.
- Data analysis template.
- Research workflow.
- Localization pack.
- Connector pack.
- Automation pack.

## Manifest Contract

Each pack must declare:

- Name.
- Version.
- Type.
- Author.
- License.
- Permissions.
- Files installed.
- Dependencies.
- Setup requirements.
- Data touched.
- Network hosts.
- Risk level.
- Uninstall plan.
- Tests.

## Safety Rules

- No pack installs without manifest validation.
- Risky packs require approval.
- Network access must be declared.
- Secrets must not be included in packs.
- Install actions must be audited.
- Rollback must be available where possible.

## Tests

Add tests for:

- Valid pack installs.
- Invalid manifest fails.
- Secret-containing pack fails.
- Risky permission requires approval.
- Pack update preserves user data.
- Rollback restores prior version.

## Acceptance Criteria

- keprix has a usable Hub.
- Builders can install packs safely.
- App templates can be distributed.
- Domain knowledge packs can be versioned.
- All installs are auditable and reversible where practical.
