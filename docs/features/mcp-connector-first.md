# MCP connector-first

Stub for Prompt 296: prefer connected MCP / integration connectors over browser scraping. Suggest connect for catalogued but disconnected servers; never invent fake MCP outputs.

Implemented by `keprix.agent.connector_router` and enforced in the tool executor before browser-style tools run.

## Related

- [Built-in tools](tools.md)
- [Resource-scoped tool ACL](resource-tool-acl.md)
- [Graphiti bridge](graphiti-bridge.md) (optional Graphiti MCP)
- Environment: `KEPRIX_AUTO_MCP_SPAWN`, `KEPRIX_MCP_ALLOWED_SERVERS` in [Environment variables](../configuration/environment-variables.md)
