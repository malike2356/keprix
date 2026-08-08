# Keprix Prompt 205: TUI Slash Commands with Gateway Fallthrough and Tab Completion

## Purpose

Expand TUI slash commands from the local subset (`/help`, `/quit`, ...) to **Hermes-scale
coverage**: local registry first, then backend `slash.exec` / `command.dispatch` fallthrough,
with **tab completion** for slash names and paths.

No visual change to composer; behavior only.

---

## Hermes reference

| File | What to port |
| --- | --- |
| `ui-tui/src/app/slash/registry.ts` | `SLASH_COMMANDS` (~40 built-ins) |
| `ui-tui/src/app/slash/createSlashHandler.ts` | Stale guard, fallthrough, pager |
| `ui-tui/src/hooks/useCompletion.ts` | `complete.slash`, `complete.path` RPC |
| `src/keprix/apps/desktop/src/lib/desktop-slash-commands.ts` | Local vs exec split |

Keprix existing:

- `src/keprix/slash/executor.py`, `slash/builtins.py`
- `src/keprix/keprix_cli/slash_commands.py`
- `src/keprix/interfaces/web_ui_stream.py` (slash in web chat)

---

## Dependencies

- `src/keprix/tui/slash_commands.py`
- `src/keprix/tui/app.py`
- Auth token in `KeprixClient`

---

## Architecture

```
User types /foo bar
       |
       v
+------------------+
| Local registry   |  /help /quit /busy /clear /copy /queue /model /sessions ...
+--------+---------+
         | miss
         v
+------------------+
| POST /api/slash/exec |  wraps execute_context(build_context(...))
+--------+---------+
         | miss or command.dispatch
         v
+------------------+
| POST /api/command/dispatch |  skills, aliases, exec directives
+------------------+
```

### Backend routes

```python
POST /api/slash/exec
  body: { "command": "memory search foo", "session_id": "...", "platform": "tui" }
  returns: { "ok": bool, "output": str, "pager": bool }

POST /api/slash/complete
  body: { "prefix": "/mem", "session_id": "..." }
  returns: { "candidates": ["/memory search", "/memory save"] }

POST /api/slash/complete-path   # optional phase 2
  body: { "prefix": "~/proj", "cwd": "..." }
```

Reuse `keprix.slash.executor.build_context` with `platform="tui"`, `session_id`, `user_id`
from auth.

**Stale session guard**: include `session_id` in request; if TUI switched sessions while
request in flight, discard response (Hermes `createSlashHandler` pattern).

---

## Local registry (minimum set)

Port these Hermes locals into `src/keprix/tui/slash_registry.py`:

| Command | Action |
| --- | --- |
| `/help` | Local help + link to docs |
| `/quit` `/exit` | Quit |
| `/new` | New chat |
| `/sessions` | Focus session list |
| `/model` | Cycle or open model list overlay (text list, no new UI chrome) |
| `/busy` | Mode toggle (201) |
| `/steer` | Steer text (201) |
| `/interrupt` `/stop` | Interrupt |
| `/queue` | Show queue |
| `/clear` | Clear transcript |
| `/copy` | Copy last reply |
| `/reconnect` | Reconnect |
| `/details` | Delegate to 206 or stub message |
| `/mouse` | Toggle mouse mode at runtime |

All others fall through to backend.

---

## Tab completion

Replace `Input` with `Input` subclass `SlashInput` in `src/keprix/tui/widgets/slash_input.py`:

- On `Tab`: if line starts with `/`, call `complete` API, cycle candidates
- On `Shift+Tab`: reverse cycle
- Show completion hint in status bar (not a new widget): `Completion: /memory search`

Debounce API 150ms.

---

## Long output pager

When `pager: true` or output lines > 40:

- Push `PagerScreen` modal (Textual `RichLog` + keys j/k, g/G, Space, q/Esc)
- Hermes-compatible key legend in footer

---

## Tests

```
tests/tui/test_slash_registry.py
tests/tui/test_slash_fallthrough.py   # mock HTTP
tests/api/test_slash_exec_api.py
tests/api/test_slash_complete_api.py
```

- Local `/help` never hits network
- `/memory search x` calls slash exec with full string
- Unknown `/zzz` returns friendly error
- Session stale guard drops late response
- Tab completion returns sorted prefixes

---

## Acceptance criteria

- [ ] At least 30 backend slash commands work from TUI via fallthrough (document list in
  `docs/reference/cli.md` TUI section)
- [ ] Tab completes `/mem` to `/memory` variants
- [ ] Long output uses pager, does not flood transcript
- [ ] Works with developer mode auth
- [ ] No new visual theme; completion hint in existing status bar only

---

## Out of scope

- Skill authoring from TUI
- MCP management UI (use web admin)
