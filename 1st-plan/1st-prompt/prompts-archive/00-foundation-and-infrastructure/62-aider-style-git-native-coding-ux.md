# keprix - Prompt 62: Aider-Style Git-Native Coding UX

## Context

Prompt 55 gives Keprix patch trajectories. This prompt extends the coding agent with Aider-style developer ergonomics: repo maps, chat-to-edit loops, git commits, lint and test integration, file watching, voice-to-code, image and URL context, and copy-paste export for web chat fallbacks.

Do not duplicate Prompt 55. Extend `backend/coding/`.

## Working Directory

`/opt/lampp/htdocs/verlox/keprix/keprix/`

## Reference To Study

Read:

```text
planning/agents-to-adopt/aider/README.md
planning/agents-to-adopt/aider/aider
planning/prompts/55-swe-agent-style-self-coding-and-patch-trajectories.md
```

## Files To Create Or Extend

```text
backend/coding/
  repo_map.py
  git_workflow.py
  lint_test_runner.py
  watch_mode.py
  voice_to_code.py
  context_loader.py
  web_chat_export.py
frontend/src/components/coding/RepoMapPanel.tsx
frontend/src/components/coding/GitCommitPanel.tsx
frontend/src/components/coding/TestRunPanel.tsx
tests/coding/test_repo_map.py
tests/coding/test_git_workflow.py
tests/coding/test_context_loader.py
```

## Required Features

### Repo Map

Build a compact map of the codebase:

- Files.
- Symbols.
- Imports.
- Routes.
- Tests.
- Recently changed files.
- Git blame metadata where available.

Use tree-sitter or language-specific parsers where available. Fall back to text scanning.

### Git Workflow

Support:

- Show diff.
- Stage selected files.
- Commit with generated message.
- Revert only keprix-created changes.
- Branch creation for risky work.
- Optional auto-commit after successful tests.

Never discard user changes without explicit approval.

### Lint and Test Loop

Allow the agent to:

- Detect test commands.
- Run lint.
- Run targeted tests.
- Parse failures.
- Repair.
- Re-run.
- Stop after max repair attempts.

### Context Inputs

Accept:

- Local files.
- URLs.
- Screenshots.
- Images.
- Voice transcription.
- Clipboard paste.

All inputs become trace artifacts.

## Acceptance Criteria

- A coding chat can edit a small repo, run tests, and propose a commit.
- Repo map excludes ignored folders and secrets.
- Watch mode reacts to changed files without infinite loops.
- Voice-to-code produces a normal coding request after transcription.
- Web chat export produces a clean context bundle when local models are unavailable.

