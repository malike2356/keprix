# Community Edition scope

Keprix Community Edition (CE) is a self-hosted AI agent OS. This page clarifies what ships in the open-source tree.

## Included in CE

- Workspace UI, agent runtime, playbooks, tools, memory, and MCP integrations
- Optional governance connector (Labyrinth Scout); see [Governance](governance.md)
- Defensive security personas and audit tooling (configuration review, dependency advisories)
- MIT licence; deploy on your own infrastructure

## Not included in CE

- Managed multi-tenant SaaS hosting or remote licence validation
- Built-in offensive exploitation or authenticated vulnerability scanning
- Enterprise SOC operations with vendor SLA (use your own processes or optional connectors)
- White-label hosted agent marketplaces

## Optional connectors

Some capabilities are available through optional, separately licensed connectors documented under [Integrations](../integrations/scout.md). CE docs do not imply these connectors ship enabled by default.

## Engineering inventory

Feature extraction metadata lives in `src/keprix/extraction/inventory.yaml` for maintainers classifying ports and connectors. It is not an operator-facing product catalogue.
