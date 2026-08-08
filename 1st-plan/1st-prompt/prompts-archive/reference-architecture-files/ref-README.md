# Architecture maps (`ref-*.md`)

These files are **dependency maps and build-order outlines**. They do not ship
code and are not placed in `pending-prompts/`.

They previously lived in `reference/`; that folder was removed. All maps now sit
in this flat archive with a `ref-` prefix.

| File | Role |
| --- | --- |
| `ref-292-fable-class-product-power-master-reference.md` | Fable-class product power map |
| `ref-292-fable-class-product-power-build-order.md` | Prompts 292-297 order |
| `ref-301-agent-os-ui-polish-master-reference.md` | Agent OS UI polish map |
| `ref-301-agent-os-ui-polish-build-order.md` | Prompts 301-315 order |
| `ref-138-chat-mutation-e2e-wiring-outline.md` | Chat mutation series (139-143) |
| `ref-144-llm-usage-analytics-wiring-outline.md` | LLM usage series (145-148) |
| `ref-149-mutation-engine-architecture-reference.md` | Mutation engine series (150-155) |
| `ref-158-autonomous-mcp-00-architecture-reference.md` | Autonomous MCP series (159-161) |

When adding a new multi-prompt series, add `ref-<series>-*.md` here, not under
`pending-prompts/`. See also [README.md](./README.md) filename conventions.
