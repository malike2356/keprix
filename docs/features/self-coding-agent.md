# Self-coding agent

The self-coding agent runs long-horizon software engineering tasks inside an isolated coding workspace. Unlike the reactive [Mutation Engine](agent.md) which synthesises individual tools on demand, the self-coding agent accepts a high-level engineering brief and executes a multi-step plan: reading code, running tests, editing files, committing changes, and iterating.

## When to use it

| Use case | Route to use |
| --- | --- |
| Fix a bug in a repository | Self-coding agent (`/admin/coding`) |
| Add a new feature with tests | Self-coding agent |
| Auto-generate a Python utility the agent needs once | Mutation Engine (`/review-gateway`) |
| Run a quick one-off code snippet | Chat with code execution tool |

## Web UI (`/admin/coding`)

1. Open **Admin > Coding** from the sidebar.
2. Choose or upload a repository (local path or Git URL).
3. Enter a task description: be specific about what file, what behaviour, what test should pass.
4. Click **Run**. The agent streams its plan, actions, and diffs in real time.
5. Review the diff and approve, reject, or iterate with a follow-up message.

## How it works

The coding agent uses a specialised system prompt and a restricted tool subset:

- **Read**: read any file in the repository
- **Edit**: apply a targeted string replacement
- **Write**: create a new file
- **Bash**: run shell commands (tests, linters, builds) inside the isolated workspace
- **Search**: grep for symbols and strings across the codebase

It plans its approach, executes steps, runs tests after each change, and self-corrects if tests fail. The loop continues until the task is complete, tests pass, or the iteration limit is reached.

The workspace is isolated per session. Host files are not accessible unless explicitly mounted.

## Configuration

```bash
KEPRIX_CODING_ENABLED=true
KEPRIX_CODING_WORKSPACE_DIR=/tmp/keprix-coding   # isolated per session
KEPRIX_CODING_MAX_ITERATIONS=50
KEPRIX_CODING_REQUIRE_APPROVAL=true              # require diff approval before git commit
KEPRIX_CODING_DEFAULT_MODEL=anthropic/claude-opus-4-8  # override model for coding tasks
KEPRIX_SANDBOX_TIMEOUT=120                       # seconds for each shell command
```

## Supported languages and stacks

Any language that can be run with a shell command works. The agent is tested against:

- Python (pytest, ruff, black)
- TypeScript / JavaScript (pnpm, npm, jest, eslint)
- Go (go test, go vet)
- Rust (cargo test, cargo clippy)
- PHP (composer, phpunit, phpstan)
- Shell scripts (shellcheck, bats)

## API

| Action | Method | Endpoint |
| --- | --- | --- |
| Start coding session | POST | `/api/code-agent/sessions` |
| Send message to session | POST | `/api/code-agent/sessions/{id}/messages` |
| Get session events | GET | `/api/code-agent/sessions/{id}/events` |
| Approve diff | POST | `/api/code-agent/sessions/{id}/approve` |
| Reject and iterate | POST | `/api/code-agent/sessions/{id}/reject` |
| List sessions | GET | `/api/code-agent/sessions` |

## Connecting a repository

**Local path**: mount a directory into the Docker workspace (see `docker-compose.yml` volumes section). Set `KEPRIX_CODING_WORKSPACE_DIR` to the container path.

**Git clone**: in the coding UI, enter a Git URL. The agent clones it into the sandbox and can push commits back if credentials are mounted.

**Upload**: drag a `.zip` of the project onto the coding workspace upload area.

## Approvals and commits

With `KEPRIX_CODING_REQUIRE_APPROVAL=true` (default), the agent presents a unified diff before writing files or running `git commit`. You approve, reject, or ask for changes. Approvals are logged to the audit trail.

Disable approval for fully automated pipelines at your own risk: `KEPRIX_CODING_REQUIRE_APPROVAL=false`.

## Relationship to Mutation Engine

The coding agent and Mutation Engine share the same sandbox infrastructure but serve different purposes:

| Feature | Mutation Engine | Self-coding agent |
| --- | --- | --- |
| Trigger | Capability gap in chat | Explicit engineering task |
| Scope | Single Python tool function | Entire repository |
| Output | Registered agent tool | Code diff / commits |
| Approval | Required (default) | Required (default) |
| Persistence | Tool installed permanently | Changes in repository |

## Troubleshooting

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| Agent cannot read files | Path outside workspace | Mount correct directory; check `KEPRIX_CODING_WORKSPACE_DIR` |
| Tests not found | Wrong test runner command | Specify test command explicitly in the task description |
| Loop exits early | Iteration limit reached | Increase `KEPRIX_CODING_MAX_ITERATIONS` or break task into steps |
| Diff rejected but no follow-up | Session expired | Restart session; past diffs are preserved in session log |

## Related

- [Agent runtime and Mutation Engine](agent.md)
- [Built-in tools](tools.md)
- [Review gateway](../security/review-gateway.md)
- [Agent Studio](agent-studio.md)
