# Keprix - Prompt 212: Operator Instance Copilot (Playbooks, Mutations, Channels)

## Purpose

Close gap **P5** (#5 in capability matrix) from `planning/competitor-research/agents-to-adopt/n8n/GAPS-FOR-KEPRIX.md`.
Study n8n `instance-ai` orchestrator pattern. Ship a **context-aware operator assistant** inside the
workspace for playbooks, staged mutations, interrupted runs, and channel errors. Not a clone of n8n credential UI.

## Already built (do not reimplement)

| Area | Location |
| --- | --- |
| Workspace chat | `frontend/src/app/(workspace)/chat/` |
| Mutation approval | `MutationCard.tsx`, `/admin/mutations` |
| Playbook runs | `/playbooks`, `[runId]` detail |
| Channel admin | `/admin/channels`, `ChannelHealthStrip` |
| Support page shell | `frontend/src/app/(workspace)/support/page.tsx` |
| Agent runtime | `src/keprix/agents_runtime/` |

## Gap

No dedicated copilot that loads **instance context** (staged mutations count, interrupted playbooks, channel health)
and suggests fixes. General chat does not inject operator dashboard state.

## Working directory

`/opt/lampp/htdocs/verlox/keprix/`

## Reference (read only)

- `planning/competitor-research/agents-to-adopt/n8n/packages/@n8n/instance-ai/README.md`
- `planning/competitor-research/agents-to-adopt/n8n/GAPS-FOR-KEPRIX.md` (P5)

## Step 1: Operator context aggregator (backend)

Create `src/keprix/operator/context_bundle.py`:

```python
@dataclass
class OperatorContextBundle:
    staged_mutations: int
    interrupted_playbooks: int
    channel_issues: list[dict[str, str]]
    recent_failed_runs: list[dict[str, str]]
    summary_markdown: str

async def build_operator_context(workspace_id: str = "default") -> OperatorContextBundle: ...
```

Data sources:

- `fetchMutationStats()` equivalent server-side
- `playbook_registry.list_runs` filtered interrupted
- `fetchChannelStatus` from admin dashboard API internals
- Last 3 failed playbook runs

Add route:

```python
GET /api/operator/context
```

Returns JSON bundle (no secrets).

## Step 2: Copilot session mode

Create `src/keprix/operator/copilot.py`:

- System prompt: "Keprix operator copilot" with injected `summary_markdown`
- Tools (read-only v1): `list_staged_mutations`, `list_interrupted_playbooks`, `get_channel_status`, `get_playbook_run_summary`
- Tools (mutating, approval-gated): `approve_mutation` (delegates existing API), `resume_playbook_run` (existing resume route)

Wire `POST /api/operator/copilot/message` streaming NDJSON (reuse `web_ui_stream` patterns or thin wrapper).

## Step 3: Frontend panel

Create `frontend/src/components/operator/OperatorCopilotDrawer.tsx`:

- Entry: floating button on workspace shell OR section on `/control-center` / `/hub`
- On open: fetch `GET /api/operator/context`, show summary chips (staged, interrupted, channels)
- Chat thread using existing `MessageFeed` / `ChatInputBar` components
- Suggested prompts chips:
  - "What needs my approval?"
  - "Why did my last playbook fail?"
  - "Which channel is unhealthy?"

Add route `frontend/src/app/(workspace)/control-center/page.tsx` panel section if page exists; else add to `/hub`.

## Step 4: Navigation

Add "Operator copilot" to `frontend/src/lib/navigation.ts` under Support or Control (badge when `staged + interrupted > 0`).

## Step 5: Tests

- `tests/operator/test_context_bundle.py`: mocked stores return expected counts
- `tests/operator/test_copilot_tools.py`: read-only tools do not mutate without approval flag
- Frontend smoke: drawer opens, loads context (manual AC)

## Acceptance criteria

| # | Test |
| --- | --- |
| 1 | `GET /api/operator/context` returns staged count and interrupted playbooks |
| 2 | Copilot answers "what needs approval" using live staged count (integration test with fixtures) |
| 3 | UI drawer shows context chips and accepts messages |
| 4 | Mutating tools require explicit user confirmation in stream (approval card) |
| 5 | `pytest tests/operator/` passes |
| 6 | No n8n code copied; operator copy says "Keprix" not "n8n" |

## Dependencies

- Prompts 194, 209 (playbook run UI) recommended for richer copilot answers.

## Archive

`prompts-archive/` when AC pass.
