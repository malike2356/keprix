# Recorded-session snapshot tests

**Status:** Implemented (prompt 772, 2026-09-20)
**Package:** `keprix.trajectory.recorded`
**Fixtures:** `tests/fixtures/trajectories/`
**Tests:** `tests/trajectory/test_recorded_session_snapshots.py`

## Intent

Catch Soft Wall, tool-routing, and loop-structure regressions **without live LLM
API keys**. Steal the DeepSeek Harness snapshot / recorded-session *idea*.
Implement on Keprix pytest using 770 trajectory replay (`mode=recorded`).

Do not import Cordis. Do not auto-write fixtures from CI.

## Fixture format (schema_version 1)

JSON object:

| Field | Purpose |
| --- | --- |
| `fixture_id` | Stable id (matches filename stem) |
| `expectations` | Structural asserts (tools, Soft Wall, mutation stages, message shape) |
| `events` | Ordered trajectory events (`seq`, `event_type`, `payload`, …) |

Shipped fixtures:

1. `soft-wall-deny.json` - Soft Wall denial on `terminal`
2. `multi-tool-success.json` - `read_file` then `memory_search`, both allowed
3. `mutation-propose-stub.json` - mutation `propose` without mount (update after 773)

## Offline harness

```python
from pathlib import Path
from keprix.trajectory.recorded import run_recorded_fixture

report = run_recorded_fixture(
    Path("tests/fixtures/trajectories/soft-wall-deny.json"),
    sqlite_path=Path("/tmp/traj-fixture.db"),
)
assert report.soft_wall_outcomes == ["denied"]
```

`run_recorded_fixture`:

1. Loads and scrubs the fixture
2. Imports events into an ephemeral SQLite trajectory store
3. Calls `TrajectoryService.replay(..., mode="recorded")`
4. Asserts expectations (tool order, Soft Wall outcomes, mutation stages,
   final message shape)
5. Guarantees every replay step has `execute=false` and `use_recorded_result=true`

No network LLM provider is opened.

## Re-record workflow (owner / local only)

When behaviour intentionally changes:

1. Reproduce the loop locally (or synthesize events via `TrajectoryService`).
2. Export a scrubbed fixture:

```python
from pathlib import Path
from keprix.trajectory import get_trajectory_service
from keprix.trajectory.recorded import export_recorded_fixture

svc = get_trajectory_service()
export_recorded_fixture(
    svc,
    "<trajectory_id>",
    fixture_id="soft-wall-deny",
    path=Path("tests/fixtures/trajectories/soft-wall-deny.json"),
    expectations={
        "require_recorded_replay": True,
        "forbid_live_execute": True,
        "tool_names_in_order": ["terminal"],
        "soft_wall_outcomes": ["denied"],
        "mutation_stages": [],
        "final_event_type": "message",
        "final_message_shape": {"role": "assistant", "status": "blocked"},
    },
    title="Soft Wall denial on terminal",
    description="Updated after policy change YYYY-MM-DD",
)
```

3. Review the JSON: no tokens, customer data, or vault secrets.
4. Run:

```bash
uv run pytest tests/trajectory/test_recorded_session_snapshots.py -q
```

5. Commit the fixture + expectation edits together.

**Never** let CI rewrite fixtures. Re-recording is a deliberate local step.

## Scrubbing

`scrub_fixture_dict` / `write_fixture` run `redact_payload` on payloads and
expectation blobs. `validate_fixture_dict` fail-closes if obvious token markers
(`sk-live-`, `ghp_`, …) remain.

## CI

Root `.github/workflows/ci.yml` backend job runs `pytest tests/` with no LLM
secrets required. An explicit step also runs the recorded-session file under
`env -u OPENAI_API_KEY -u ANTHROPIC_API_KEY`.

## Non-goals

- Golden LLM quality scoring / full eval suite
- Cordis snapshot runner
- Browser video recording
- Silent CI fixture updates

## Related

- Session trajectory: `docs/architecture/session-trajectory.md` (770)
- Mutation-as-mount: prompt 773 (update mutation fixture when it lands)
