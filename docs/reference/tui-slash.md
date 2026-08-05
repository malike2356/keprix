# TUI Slash Commands

The Textual TUI uses a local registry first, then backend fallthrough:

1. Local commands (`/help`, `/busy`, `/new`, ...) run in the client.
2. `POST /api/slash/exec` runs registered backend slash commands (`/status`, `/memory search`, `/tools`, ...).
3. `POST /api/command/dispatch` handles skills, aliases, queue/retry/steer send paths, and plugin commands.

The slash popup shows command names and descriptions. Use Up and Down to move, Tab or Enter to accept the selected command, and Esc to close the popup.

## Local commands

| Command | Aliases | Description | Arguments |
| --- | --- | --- | --- |
| `/help` | `/?` | Show local and backend command help | |
| `/quit` | `/exit`, `/q` | Exit the TUI | |
| `/new` | | Start a new chat | |
| `/sessions` | | Focus the session list | |
| `/model` | | Cycle the active model | `[query]` |
| `/setup` | | Run full setup wizard | |
| `/busy` | | Show or set busy input mode | `interrupt\|queue\|steer` |
| `/steer` | | Inject guidance into the current turn | `<instruction>` |
| `/interrupt` | `/stop` | Stop the current reply | |
| `/queue` | | Show queued messages | |
| `/clear` | | Clear the transcript | |
| `/copy` | | Copy the last agent reply | |
| `/reconnect` | | Reconnect to the backend | |
| `/details` | | Show or set details section visibility | `[section mode]` |
| `/voice` | | Enable or disable push-to-talk voice | |
| `/mouse` | | Toggle mouse capture at runtime | |
| `/compact` | | Compact the active transcript | |
| `/tools` | | Search available tools | |
| `/skills` | | Browse or manage skills | |
| `/plugins` | | Browse or manage plugins | |
| `/config` | | Show or edit configuration | |
| `/doctor` | | Run local diagnostics | |
| `/insights` | | Show session insights | |
| `/resume` | | Resume a previous session | |
| `/fork` | | Fork the active session | |
| `/theme` | | Change the active theme | |
| `/skin` | | Change the active skin | |
| `/export` | | Export session data | |
| `/import` | | Import session data | |
| `/feedback` | | Send product feedback | |
| `/debug` | | Toggle debug overlay | |
| `/open` | | Open a URL in the system browser | `<url>` |
| `/search` | | Search the current transcript | `<query>` |
| `/profile` | | Switch or inspect profile | |
| `/cron` | | Manage scheduled jobs | |
| `/gateway` | | Inspect gateway connection | |
| `/agent` | | Inspect sub-agents | |
| `/mcp` | | Manage MCP servers | |
| `/hub` | | Open the hub | |
| `/billing` | | Show billing state | |
| `/usage` | | Show usage counters | |
| `/status` | | Show system status | |
| `/restart` | | Restart the current runtime | |

Some commands are local panels. Some commands call backend endpoints when a backend is available. Backend failures should produce a short unavailable message, not a raw stack trace.

## Backend examples (30+ via fallthrough)

| Command | Description |
| --- | --- |
| `/status` | Agent and gateway status |
| `/whoami` | Current identity |
| `/memory search <query>` | Search memory |
| `/memory save "text"` | Save memory |
| `/playbook scan` | Hardware scan |
| `/playbook models` | List local models |
| `/tools` | List enabled tools |
| `/tool run <name> <json>` | Run a tool |
| `/research "query"` | Start research job |
| `/settings` | Settings summary |
| `/settings set <key> <value>` | Change setting |
| `/channels` | Connected channels |
| `/governance status` | Governance status |
| `/data profile <dataset>` | Dataset profile |
| `/data export <dataset>` | Export dataset |
| `/jobs` | Active/failed jobs |
| `/jobs retry <id>` | Retry job |
| `/research project "title"` | Create research project |
| `/stats describe <dataset> <column>` | Descriptive stats |
| `/stats codebook <dataset>` | Codebook |
| `/ml experiment <dataset>` | ML experiment |
| `/ml runs` | ML runs |
| `/opportunity find ...` | Opportunity playbooks |
| `/crew <team> "objective"` | Agent team run |
| `/language set ...` | Language preferences |
| `/safety` | Safety rules |
| `/approve <token>` | Approve pending action |
| `/cancel <token>` | Cancel pending action |
| `/diagnostics` | Diagnostics |

## Keyboard behavior

| Key | Behavior |
| --- | --- |
| `Tab` | Accept selected completion, or complete the unique match |
| `Enter` | Accept selected slash completion when the popup is open, otherwise submit |
| `Up` / `Down` | Move through slash suggestions or history depending on focus |
| `Esc` | Close completion, overlay, or panel |
| `Ctrl+P` | Command palette |
| `Ctrl+G` | External editor compose |
| `Ctrl+B` | Voice push-to-talk when enabled |
| `Ctrl+L` | Clear transcript |
| `Ctrl+S` | Focus sessions |
| `Ctrl+M` | Cycle model |
| `Ctrl+R` | Reconnect |
| `Ctrl+Shift+R` | Review mode |
| `Ctrl+K` | Search |
| `Ctrl+C` | Interrupt current turn |

Long output opens a pager when output exceeds the configured output threshold.

## Safety and sanitization

The TUI must not expose raw implementation errors in normal command output. In particular, command failures should hide:

- Raw `HTTPStatusError` strings.
- Full backend tracebacks.
- `user_id`, `workspace_id`, `channel`, `channel_user_id`, and role markers from internal context.
- Secrets, tokens, and credential material.

Launch:

```bash
PYTHONPATH=src python3 -m keprix tui
PYTHONPATH=src python3 -m keprix tui --mouse
```
