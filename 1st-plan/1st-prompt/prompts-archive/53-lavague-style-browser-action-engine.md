# keprix - Prompt 53: LaVague-Style Browser Action Engine

> **Status (2026-07-05):** Implemented under `src/keprix/browser/` and mounted on `src/keprix/api/server.py`. Playwright/Selenium drivers, extension bridge stub, QA runner, element map, screenshot store, approval gates, and tests are in place. Set `KEPRIX_BROWSER_ALLOW_STUB=false` in production and install Playwright (`pip install playwright && playwright install chromium`).

## Context

Adopt LaVague's browser automation architecture into keprix.

keprix needs a governed browser agent that can use public websites, dashboards, forms, CRMs, and internal tools. It must be transparent, logged, and approval-led.

## Working Directory

`/opt/lampp/htdocs/verlox/keprix/keprix/`

## Reference To Study

Read:

```text
planning/agents-to-adopt/lavague/README.md
planning/agents-to-adopt/lavague/lavague-core/lavague/core
planning/agents-to-adopt/lavague/lavague-integrations/drivers
planning/agents-to-adopt/lavague/lavague-qa
planning/agents-to-adopt/lavague/extension_chrome
```

## Files To Create

```text
backend/browser/
  __init__.py
  world_model.py
  action_engine.py
  drivers.py
  playwright_driver.py
  selenium_driver.py
  chrome_extension_bridge.py
  element_map.py
  screenshots.py
  action_log.py
  qa_runner.py
  safety.py
tests/browser/test_world_model.py
tests/browser/test_action_engine.py
tests/browser/test_browser_safety.py
```

## Architecture

Implement:

- World Model: converts objective and current page state into next instruction.
- Action Engine: compiles instruction into safe browser actions.
- Drivers: Playwright, Selenium, and Chrome extension bridge.
- Element Map: captures visible elements, labels, roles, coordinates, iframe context.
- Action Log: stores every planned and executed action.
- Screenshot Store: before and after screenshots for risky actions.

## Supported Actions

Safe by default:

- Navigate.
- Read page.
- Search public site.
- Click non-destructive elements.
- Fill draft fields.
- Extract visible public data.
- Take screenshot.

Approval required:

- Submit forms.
- Send messages.
- Publish content.
- Delete records.
- Download sensitive data.
- Upload files.
- Purchase or pay.
- Change settings.
- Change ad budgets.
- Modify CRM records.

## QA Mode

Adopt LaVague QA ideas:

- Convert Gherkin-style scenarios into browser tests.
- Run against local or staging URLs.
- Capture screenshots and failure traces.
- Export test reports.

## Telemetry Policy

keprix is privacy-first:

- No external telemetry by default.
- Local action logs only.
- Redact secrets and personal data from logs.
- Let the developer opt in to local-only debug capture.

## API Routes

Add:

```text
POST /api/browser/session
POST /api/browser/{session_id}/run
POST /api/browser/{session_id}/approve
GET /api/browser/{session_id}/actions
GET /api/browser/{session_id}/screenshot/{id}
POST /api/browser/qa/run
```

## Acceptance Criteria

- Browser agent can inspect a page and propose actions.
- Risky actions pause for approval.
- Every action is logged with screenshot support.
- Playwright driver works in headless mode.
- Chrome extension bridge has a safe stub if extension is not installed.
- QA runner can execute a simple Gherkin scenario.
- Tests cover approval gates, iframe element mapping, redaction, and action log integrity.

