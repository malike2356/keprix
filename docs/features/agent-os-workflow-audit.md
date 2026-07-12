# Agent OS workflow audit

The workflow audit wizard is the Level 1 entry point for the Agentic OS adoption pack (prompt **256**).

## Routes

| Route | Purpose |
| --- | --- |
| `/agent-os/audit` | Three-mode audit wizard |
| `POST /api/agent-os/audit/start` | Start manual, session scan, or interview audit |
| `POST /api/agent-os/audit/{id}/complete` | Finalize proposed skills |
| `GET /api/agent-os/audits` | List saved audits |
| `POST /api/agent-os/audit/{id}/export-to-proposals` | Queue proposals for prompt **257** |

## CLI

```bash
keprix agent-os audit start --mode manual
keprix agent-os audit list
keprix agent-os audit show <audit_id>
keprix agent-os audit export <audit_id> --to-proposals
```

## Disable

Set `KEPRIX_AGENT_OS_ENABLED=0` to hide Agent OS API routes.

## Proposal contract

Export writes pending rows to `{KEPRIX_HOME}/agent-os/skill-proposals-pending.json`.
Prompt **257** imports rows with `source: "audit"`, `origin: "workflow_audit"`,
`audit_id`, `slug`, `name`, `description`, `evidence_sessions`, and `status`.

## Next steps

After an audit, promote skills carefully. Tool calls from promoted skills still pass product and resource ACL gates; see [resource-tool-acl](resource-tool-acl.md).

- Prompt **257**: approve exported proposals as skills
- Prompt **258**: apply Knowledge Pipeline workspace template
