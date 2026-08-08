# keprix - Prompt 55: SWE-Agent-Style Self-Coding and Patch Trajectories

## Context

Adopt SWE-agent's strongest software engineering patterns into keprix.

keprix already has self-coding direction. This prompt upgrades it with issue-to-patch workflows, repo filemaps, scoped file edits, trajectory logs, benchmark tasks, configurable agent profiles, and safer review loops.

## Working Directory

`/opt/lampp/htdocs/verlox/keprix/keprix/`

## Reference To Study

Read:

```text
planning/agents-to-adopt/swe-agent/README.md
planning/agents-to-adopt/swe-agent/config
planning/agents-to-adopt/swe-agent/sweagent/agent
planning/agents-to-adopt/swe-agent/sweagent/tools
```

## Files To Create

```text
backend/coding/
  __init__.py
  issue_runner.py
  filemap.py
  patcher.py
  scoped_replace.py
  trajectory.py
  benchmark.py
  review.py
  configs.py
  parsers.py
tests/coding/test_issue_runner.py
tests/coding/test_scoped_replace.py
tests/coding/test_trajectory.py
tests/coding/test_filemap.py
```

## Required Features

### Issue-To-Patch Runner

Input:

- GitHub issue URL or text.
- Local repo path.
- Constraints.
- Test command.
- Approval policy.

Output:

- Patch.
- Explanation.
- Tests run.
- Risk notes.
- Trajectory log.

### Filemap

Build a repo map:

- Package files.
- Entry points.
- Tests.
- Routes.
- Config.
- Recently changed files.
- Symbols if parser is available.

### Scoped Replace

Implement safe edit operations:

- Replace exact block.
- Insert before.
- Insert after.
- Append to file.
- Create file.

Every edit must include:

- Old content hash.
- New content hash.
- Diff preview.
- Rollback data.

### Trajectory Logs

Record:

- Prompt.
- Tool call.
- File read.
- Edit proposal.
- Test command.
- Test output summary.
- Decision.
- Approval.
- Final patch.

Store under:

```text
workspace/coding-trajectories/{run_id}.jsonl
```

### Config Profiles

Support YAML profiles:

- `default`
- `bash_only`
- `human_review`
- `filemap_review`
- `coding_challenge`
- `locked_down`

## Guardrails

- Never run destructive Git commands without approval.
- Never edit outside the selected repo.
- Never commit without approval.
- Never push without approval.
- Never expose secrets in trajectory logs.

## Acceptance Criteria

- keprix can take an issue and produce a patch.
- Patches are scoped and reversible.
- Tests can run and summaries are stored.
- Trajectory logs are complete and redacted.
- YAML config changes agent behaviour.
- Tests cover safe edits, rollback data, secret redaction, and approval before commit/push.
