# Keprix Prompt 186: Agent Apps - Docs, Scaffold CLI, and E2E Verification

## Purpose

Close the Agent Apps product pack with **operator documentation**, developer scaffold,
marketing alignment, eval suite, and agent brief for manual golden-path verification.
After this prompt, Agent Apps is demo-ready for sales.

Read reference **177**. Requires prompts **178-185** complete.

---

## Dependencies

- All agent apps code from 178-185
- `src/keprix/keprix_cli/` (CLI commands pattern)
- `docs/features/`, `docs/integrations/sdk.md`
- `evals/suites/` pattern
- `prompts-archive/` verification pattern from other packs

---

## What to build

### 1. Operator guide

**`docs/features/agent-apps.md`** (NEW)

Sections (write fully):

1. **What are Agent Apps?** - manifest folder, vs chat vs agent studio.
2. **60-second quick start** - Discover -> Install Daily Standup -> Run -> Schedule.
3. **Installed apps** - hub, detail page, uninstall, export.
4. **Templates** - marketplace categories, Free vs Pro templates.
5. **Inputs and outputs** - dynamic forms, markdown results, artifacts.
6. **Secrets** - `required_env`, vault, readiness check.
7. **Scheduling** - cron presets, link to `/admin/cron`.
8. **Webhooks and API** - curl examples, API keys from developer portal.
9. **Run history and evals** - history tab, eval suite, agent runtime.
10. **Building your own app** - folder layout, `agent.yaml`, CLI scaffold.
11. **Billing limits** - table per plan (installs, runs, scheduling).
12. **Troubleshooting** - LLM not configured, missing env, 402 upgrade, webhook 401.

### 2. Update existing docs

| File | Change |
| --- | --- |
| `docs/index.md` | Row under Features: Agent Apps -> `features/agent-apps.md` |
| `docs/features/agent-studio.md` | Export to agent app (stub or link if implemented) |
| `docs/integrations/sdk.md` | `defineAgentApp` future note; REST run endpoint |
| `docs/reference/cli.md` | `keprix agent-app` subcommands |
| `README.md` | One paragraph + link to agent apps doc |
| `.env.example` | `KEPRIX_AGENT_APPS_DIR`, `KEPRIX_AGENT_APP_RUN_RETENTION_DAYS` |

### 3. CLI scaffold enhancements

Extend `keprix agent-app` command:

```bash
keprix agent-app create my-app --template agent|python
keprix agent-app validate ./my-app
keprix agent-app run ./my-app --input "..."
keprix agent-app bundle ./my-app -o my-app.zip
keprix agent-app catalog list
```

`create --template agent` generates v2 manifest, `instructions.md`, sample tool, eval yaml.

### 4. Eval suite

**`evals/suites/agent-apps/basics.yaml`**

Tasks (mocked LLM where needed):

- `catalog_lists_templates`
- `install_daily_standup`
- `readiness_endpoint`
- `run_returns_output`
- `usage_endpoint`
- `billing_402_on_limit` (optional mock plan)

**`evals/agent-apps/validators.py`** if custom assertions needed.

### 5. Agent brief

**`prompts-archive/186-agent-apps-golden-path-verification.md`**

Manual checklist (~15 steps):

1. Open `/agent-apps` logged in
2. Discover tab shows 3 templates
3. Install Daily Standup one click
4. Readiness green (or set env)
5. Fill form, Run, see markdown output
6. History shows run
7. Enable schedule Weekdays 9am
8. Verify cron job in `/admin/cron`
9. Rotate webhook, curl POST succeeds
10. Export bundle, uninstall, reinstall from zip
11. Pro template shows upgrade on free plan
12. Run eval suite from UI
13. CLI `keprix agent-app run` works
14. Agent runtime filter shows runs
15. Docs page readable

### 6. Marketing polish

**`frontend/src/app/(workspace)/agent-apps/page.tsx`** hub subtitle:

- User-facing copy: "Install ready-made workflows or ship your own apps."

**`/pricing`**: verify Agent Apps row from **184** is accurate.

Optional screenshot placeholder: `docs/assets/screenshots/agent-apps-hub.svg`

### 7. Navigation and discoverability

- Launcher `/launcher` card if launcher page lists features
- Hub `/hub` link tile "Agent Apps"
- Onboarding: first visit tooltip on hub (localStorage `keprix.agent_apps.intro.dismissed`)

---

## Acceptance criteria

- [ ] `docs/features/agent-apps.md` complete and linked from docs index.
- [ ] CLI `create`, `validate`, `bundle`, `catalog list` work.
- [ ] Eval suite passes in CI (mocked backends).
- [ ] Agent brief committed and executable by QA.
- [ ] No TODO stubs in user-facing strings on `/agent-apps` routes.

---

## Archive

On completion:

1. Move this file to `prompts-archive/`
2. Update `PROMPT-IMPLEMENTATION-AUDIT.md` with series **177-186** complete
3. Update `docs/DOCUMENTATION_ROADMAP.md` if it lists agent apps as missing

---

## Series summary

| # | Title |
| --- | --- |
| 177 | Architecture reference |
| 178 | Frictionless hub UI |
| 179 | Manifest v2 + dynamic forms |
| 180 | Agent execution bridge |
| 181 | Install lifecycle |
| 182 | Marketplace catalog |
| 183 | Schedule + webhooks + API |
| 184 | Billing + entitlements |
| 185 | Observability + evals UI |
| 186 | Docs + scaffold + e2e |
