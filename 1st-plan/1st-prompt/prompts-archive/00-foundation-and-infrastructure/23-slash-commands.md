# keprix - Prompt 23: Slash Commands

## Purpose

Add a first-class slash-command system to keprix. Prompt 13 mentions channel slash commands, but this prompt defines the shared registry, channel adapters, safety gates, tests, and user-facing behavior.

Slash commands are the fast command surface for common agent actions across chat, web, CLI, and team platforms. They must be deterministic, auditable, and safe to run in shared channels.

## Scope

Implement:

- A shared slash-command registry.
- Channel adapters for Telegram bot commands, Discord slash commands, Slack slash commands, Matrix command messages, WebChat commands, CLI aliases, and TUI command palette.
- Built-in commands for help, status, memory, playbook, tools, research, settings, safety, and diagnostics.
- Permission checks per command.
- Confirmation gates for destructive, external, or cyber actions.
- Audit logging for every command invocation.
- Tests for parsing, permissions, routing, and channel response formatting.

## Output Paths

Use these target paths unless the codebase evolves before implementation:

```text
keprix/backend/slash/
  __init__.py
  registry.py
  parser.py
  permissions.py
  audit.py
  schemas.py
  builtins.py
  renderers.py

keprix/backend/gateway/slash/
  telegram.py
  discord.py
  slack.py
  matrix.py
  webchat.py

keprix/backend/cli/slash_commands.py
keprix/tests/slash/
```

## Command Contract

Create a typed command contract:

```python
class SlashCommand:
    name: str
    aliases: list[str]
    description: str
    usage: str
    category: str
    min_role: str
    requires_confirmation: bool
    handler: Callable[[SlashContext], Awaitable[SlashResult]]
```

`SlashContext` must include:

- `user_id`
- `workspace_id`
- `channel`
- `channel_user_id`
- `raw_text`
- `args`
- `metadata`
- `request_id`

`SlashResult` must include:

- `ok`
- `message`
- `blocks`
- `requires_confirmation`
- `confirmation_token`
- `ephemeral`
- `audit_id`

## Built-In Commands

Ship these commands in v1:

| Command | Purpose | Safety |
| --- | --- | --- |
| `/help` | Show available commands for the current channel and user role. | Safe |
| `/status` | Show agent, model, gateway, memory, and Scout status. | Safe |
| `/whoami` | Show current user, workspace, role, and channel identity. | Safe |
| `/memory search <query>` | Search user-scoped memory. | Safe |
| `/memory save <text>` | Save a memory after preview. | Confirmation |
| `/playbook scan` | Run hardware scan and recommend local models. | Safe |
| `/playbook models` | List recommended local models and fit scores. | Safe |
| `/playbook serve <model>` | Start a local model backend. | Confirmation |
| `/tools` | List enabled tools. | Safe |
| `/tool run <name> <json>` | Run a named tool with JSON args. | Confirmation unless allowlisted |
| `/research <query>` | Start deep research. | Confirmation for web access |
| `/settings` | Show editable settings summary. | Safe |
| `/settings set <key> <value>` | Change a setting. | Confirmation |
| `/channels` | Show connected channels and health. | Safe |
| `/scout status` | Show Scout connection and governance mode. | Safe |
| `/safety` | Show active safety rules and approval requirements. | Safe |
| `/approve <token>` | Approve a pending command. | Safe but token-scoped |
| `/cancel <token>` | Cancel a pending command. | Safe |
| `/diagnostics` | Show version, uptime, queue depth, and recent errors. | Safe |

Cyber commands from prompts 21 to 34 must not run directly through slash commands unless the command is scoped to an active authorization record. Use a confirmation token and write to the cyber audit log.

## Parsing Rules

- Commands start with `/`.
- Support quoted args: `/memory save "Client prefers Monday calls"`.
- Support JSON args after `--json`.
- Support flags: `/research "market map" --depth deep --model local`.
- Unknown commands return suggestions based on edit distance.
- Commands must not fall through to normal chat unless explicitly configured.
- In group channels, require mention or platform command invocation when the platform supports it.

## Permissions

Define these roles:

- `viewer`
- `operator`
- `admin`
- `owner`

Default access:

- Read-only commands: `viewer`.
- Memory writes and research jobs: `operator`.
- Settings changes, channel changes, tool execution: `admin`.
- Security and cyber approval overrides: `owner`.

Permissions must be workspace-scoped and channel-aware. A Slack workspace user and a Telegram user must resolve to the same internal user only after explicit account linking.

## Confirmation Flow

For risky commands:

1. Parse and validate.
2. Return a preview with the exact action, target, data touched, and risk level.
3. Create a short-lived confirmation token.
4. Require `/approve <token>` or channel-native button approval.
5. Execute only after the approval identity matches the original user or an authorized admin.
6. Log both request and approval.

Tokens expire after 10 minutes by default.

## Channel Adapters

### Telegram

- Register bot commands with BotFather-compatible metadata.
- Support `/help`, `/status`, and all built-ins.
- Render confirmations with inline keyboard buttons.
- In groups, require `/command@BotName` or mention rules.

### Discord

- Register application commands.
- Support ephemeral replies for sensitive command output.
- Use buttons for approval and cancellation.
- Sync command metadata on gateway startup.

### Slack

- Support slash commands and shortcuts.
- Verify Slack signing secret before parsing.
- Use Block Kit for previews and confirmation buttons.
- Sensitive output must be ephemeral.

### Matrix And WebChat

- Matrix uses command messages, for example `/carina status`.
- WebChat supports slash autocomplete and command palette.
- Both use the shared parser and registry.

### CLI And TUI

- `keprix slash list`
- `keprix slash run "/status"`
- TUI command palette reuses registry metadata.

## Audit Log

Write every invocation to `slash_command_audit`:

```sql
CREATE TABLE slash_command_audit (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    channel TEXT NOT NULL,
    command TEXT NOT NULL,
    args_json JSONB DEFAULT '{}',
    status TEXT NOT NULL,
    risk_level TEXT NOT NULL DEFAULT 'low',
    confirmation_required BOOLEAN NOT NULL DEFAULT FALSE,
    confirmation_token_hash TEXT,
    error TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);
```

Do not store raw secrets in args. Redact API keys, tokens, passwords, private keys, cookies, and authorization headers before logging.

## API Surface

Expose:

```text
GET  /api/slash/commands
POST /api/slash/parse
POST /api/slash/execute
POST /api/slash/approve
POST /api/slash/cancel
GET  /api/slash/audit
```

All endpoints require authentication. Public channel webhooks must verify the platform signature before calling the shared executor.

## Tests

Add tests for:

- `/help` lists commands allowed for the current role.
- Unknown command returns suggestions.
- Quoted args and JSON args parse correctly.
- Viewer cannot run admin commands.
- Risky command returns confirmation instead of executing.
- Approval token executes the pending command only once.
- Expired approval token fails.
- Telegram adapter renders inline keyboard confirmation.
- Discord adapter marks sensitive responses ephemeral.
- Slack adapter rejects invalid signatures.
- Audit log redacts secrets.
- Cyber command is blocked without active authorization.

## Acceptance Criteria

- `keprix slash list` prints built-in commands.
- `keprix slash run "/status"` returns agent status.
- Telegram `/status` returns a response.
- Discord `/carina status` returns an ephemeral or channel-safe response.
- Slack `/carina status` verifies signature and returns status.
- `/playbook scan` calls the Playbook hardware scan service from Prompt 14.
- `/tool run` requires confirmation unless the tool is explicitly allowlisted.
- Every command writes an audit row.
- No slash command uses legacy model-recipe terminology in code, API routes, UI, docs, or prompts.
