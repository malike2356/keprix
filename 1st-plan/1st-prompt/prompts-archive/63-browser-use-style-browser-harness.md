# keprix - Prompt 63: Browser-Use-Style Browser Harness

> **Status (2026-07-05):** Implemented under `src/keprix/browser/` (extends Prompt 53). Harness, encrypted profiles, skills, benchmarks, cloud executor stub, API routes, frontend settings UI, and 24+ tests.

## Context

Prompt 53 adds a browser action engine inspired by LaVague. This prompt extends it with browser-use style reliability: a direct browser harness for coding agents, profile persistence, task benchmarks, browser sessions, cloud-optional execution, and reusable browser skills.

Do not duplicate Prompt 53. Extend `backend/browser/`.

## Working Directory

`/opt/lampp/htdocs/verlox/keprix/keprix/`

## Reference To Study

Read:

```text
planning/agents-to-adopt/browser-use/README.md
planning/agents-to-adopt/browser-use/browser_use
planning/prompts/53-lavague-style-browser-action-engine.md
```

## Files To Create Or Extend

```text
backend/browser/
  harness.py
  browser_profile.py
  session_store.py
  browser_skill.py
  benchmark_runner.py
  auth_context.py
  cloud_executor.py
frontend/src/components/browser/BrowserSessionPanel.tsx
frontend/src/components/browser/BrowserProfileSettings.tsx
tests/browser/test_harness.py
tests/browser/test_browser_profile.py
tests/browser/test_browser_skill.py
tests/browser/test_browser_benchmark.py
```

## Required Features

### Browser Harness

Expose a dependable browser surface to agents:

- Current page.
- DOM snapshot.
- Accessibility tree.
- Screenshot.
- Console logs.
- Network summary.
- Download events.
- File upload controls.

### Browser Profiles

Support named profiles:

- Fresh isolated profile.
- Persistent local profile.
- Authenticated profile.
- Read-only profile.
- Disposable test profile.

Credentials stay in the vault. Cookies and sessions must be encrypted at rest.

### Browser Skills

Add reusable skills:

- Form filling.
- Account setup.
- Dashboard navigation.
- Price checking.
- Report download.
- Research collection.
- Checkout dry run.

Every skill must declare risk and approval requirements.

### Benchmarks

Add local browser task benchmarks:

- Form filling.
- Search and compare.
- Login and navigate.
- Extract table.
- Download file.
- Fill but do not submit.

## Acceptance Criteria

- A coding agent can request a browser session through the harness.
- Authenticated profiles are encrypted and scoped per workspace.
- Browser skills can run as playbook nodes.
- Benchmark results include success, failure reason, screenshots, and trace IDs.
- Purchases, sends, deletes, and settings changes always require approval.

