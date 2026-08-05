# AI Service Accounts

Use dedicated integration users for AI automation instead of personal admin accounts.

## Checklist

- Create a named integration user such as `Keprix AI`.
- Scope access per domain: read-only where possible, write access only when required.
- Store credentials in Keprix credential storage or the approved connector flow.
- Rotate credentials on a fixed schedule and after team changes.
- Keep `connections.md` free of secrets; reference env keys or connector ids only.

Examples:

- Google Workspace group or service account for calendar, mail, Drive, and Sheets.
- ClickUp member for task automation.
- CRM/support user limited to queues the agent may read.
