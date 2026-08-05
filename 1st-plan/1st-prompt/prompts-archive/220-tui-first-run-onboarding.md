# Keprix - Prompt 220: TUI First-Run Onboarding (Hermes-Style, Keprix Way)

## Purpose

When a user installs Keprix and launches the **Textual TUI** without a configured LLM
provider, unblock them with a **minimal one-screen picker** (provider + API key + model).
The **canonical** first-run path remains `keprix setup` (CLI wizard, already shipped).
The **web** surface remains an operator checklist (`support/onboarding.py`), not a
duplicate install wizard.

**All three surfaces activate by entry point, not by user preference.**

This prompt covers prompts **220-222** unless split per build order reference.

## Already built (do not reimplement)

| Area | Location |
| --- | --- |
| Interactive setup wizard | `keprix_cli/setup.py` (`run_setup_wizard`, `SETUP_SECTIONS`) |
| Model/provider flows | `keprix_cli/model_setup_flows.py`, `keprix model` |
| CLI provider gate | `keprix_cli/main.py` `_has_any_provider_configured()` |
| Onboarding hint library | `agent/onboarding.py` |
| Profile build in gateway | `gateway/run.py` (first message, messaging platforms) |
| TUI chat shell | `src/keprix/tui/app.py`, `client.py`, `slash_commands.py` |
| Models list API | `GET /api/models/available` in `conversation_routes.py` |
| Web onboarding checklist | `support/onboarding.py` |

## Gap (honest)

- TUI never shows a **Setup required** state when unconfigured.
- CLI hard-exits before TUI if user declines setup at the Y/n prompt.
- No `GET /api/setup/status` for TUI/web to agree on configured vs not.
- No **minimal** TUI configure path (one screen, not full wizard).
- `profile_build_directive()` not on TUI HTTP conversation path.
- Web checklist exists but is not linked from TUI setup panel.

## Surface boundaries (hard)

| Do in CLI (`keprix setup`) | Do in TUI only | Do in web only |
| --- | --- | --- |
| Full wizard (model, TTS, terminal, gateway, tools, agent) | One-screen provider unblock | Checklist ticks, admin gaps |
| First install recommendation | Catch skipped-setup users | Team operator dashboard |
| `keprix setup --portal`, quick setup | `/setup` subprocess as **optional** escape hatch | Link to settings pages |

**Do not** ask users to choose onboarding mode in config. Surface = behavior.

## Working directory

`/opt/lampp/htdocs/verlox/keprix/`

## Reference (read only)

- `prompts-archive/ref-220-tui-first-run-onboarding-architecture-reference.md`
- `prompts-archive/ref-220-tui-first-run-onboarding-build-order.md`
- `prompts-archive/ref-tui-hermes-parity-architecture.md`
- Hermes handoff: `planning/competitor-research/agents-to-adopt/hermes-agent/ui-tui/src/app/setupHandoff.ts`
- Hermes setup panel copy: `.../ui-tui/src/content/setup.ts`

---

## Step 1: Shared setup status (backend)

Create `src/keprix/setup/status.py`:

```python
def provider_configured() -> bool: ...
def model_configured() -> bool: ...
def setup_status_snapshot() -> dict: ...
```

- Reuse the same probes as `_has_any_provider_configured()` and active model from
  `keprix_cli/config.py` / `get_active_provider()`. Extract shared logic from
  `main.py` into this module; keep `main.py` as a thin caller (no drift).
- Return JSON-safe snapshot:

```json
{
  "provider_configured": false,
  "model_configured": false,
  "active_provider": null,
  "default_model": null,
  "wizard_sections": ["model", "tts", "terminal", "gateway", "tools", "agent"],
  "docs_url": "https://keprix.nousresearch.com/docs/getting-started/first-run"
}
```

Add route `src/keprix/setup/routes.py`:

- `GET /api/setup/status` (public on localhost when `AUTH_ENABLED=false`, else optional auth)

Register router in `api/server.py`.

Tests: `tests/setup/test_setup_status.py` (configured vs fresh `tmp_path` home).

---

## Step 2: Soften CLI gate for TUI-only launch

In `keprix_cli/main.py`, when `_has_any_provider_configured()` is false:

| Launch mode | Behavior |
| --- | --- |
| Default CLI chat | Keep current behavior (prompt setup or exit) |
| `--tui` / `display.interface=tui` | **Allow TUI launch** with `KEPRIX_SETUP_REQUIRED=1` env var set |

Rationale: Hermes Ink TUI could recover in-app; Keprix Textual TUI should not be
blocked at the shell if the user declined the Y/n prompt.

Non-interactive (no TTY): keep exit with `print_noninteractive_setup_guidance()`.

---

## Step 3: TUI minimal setup screen (primary)

Create `src/keprix/tui/widgets/setup_required.py`:

- Full-width overlay when `provider_configured: false`.
- **One screen**, not a wizard replica:
  1. Provider picker (reuse list from `keprix model` / registry subset: OpenRouter, OpenAI, Anthropic, Ollama, custom URL)
  2. API key or base URL field (provider-dependent)
  3. Optional default model dropdown (populate after key validates, or skip with provider default)
  4. **Save and continue** calls a thin API `POST /api/setup/minimal` OR suspends and runs `keprix setup model` once

- Secondary actions (footer):
  - `Run full setup` -> subprocess `keprix setup` (Hermes handoff, optional)
  - `Open docs` -> print first-run URL
  - `Ctrl+C` exit

- Disable composer until configured.

Prefer **inline form** over redirect-only message. Subprocess handoff is fallback.

Update `app.py` `on_mount`: fetch status, show overlay if needed, else normal flow.

---

## Step 4: Optional setup handoff + web checklist link

**TUI (optional):** `run_setup_handoff()` for `/setup` slash when user wants full wizard.

**Web (no new wizard):** Ensure admin/support checklist reflects `GET /api/setup/status`
(auto-tick `llm-provider` when configured). Link from workspace settings if missing.

Do **not** build a web first-run wizard duplicating `keprix setup`.

---

## Step 5: First-message onboarding (TUI conversation path)

Mirror `gateway/run.py` profile-build block on the workspace conversation POST path
used by the TUI (`conversation_routes.py` or shared helper in `agent/onboarding_hooks.py`):

When **all** of:

- Session has zero prior user messages (first message in conversation)
- `profile_build_mode(config) == "ask"`
- `not is_seen(config, PROFILE_BUILD_FLAG)`

Then append `profile_build_directive()` to the system/context prompt for that turn
only, and `mark_seen(config_path, PROFILE_BUILD_FLAG)`.

Also wire one-time **OpenClaw residue** banner on first TUI mount:

- If `detect_openclaw_residue()` and not `is_seen(OPENCLAW_RESIDUE_FLAG)`: print
  `openclaw_residue_hint_cli()` to transcript; mark seen.

Busy-input and tool-progress hints: ensure TUI NDJSON stream surfaces gateway/turn
system lines when hints fire (may already work; add test if not).

Tests: `tests/tui/test_onboarding_first_message.py` or extend `tests/agent/test_onboarding.py`.

---

## Step 6: Documentation

Update:

- `docs/features/tui.md`: add "First run and setup" section; parity row for setup handoff.
- `docs/getting-started/first-run.md`: document TUI path (`keprix start`, `keprix --tui`, `/setup`).
- `docs/reference/cli.md`: note `--tui` launches even when unconfigured (setup mode).

---

## Acceptance criteria

| # | Test |
| --- | --- |
| 1 | Fresh install: `GET /api/setup/status` returns `provider_configured: false` |
| 2 | After `keprix setup model` in temp home, status returns `true` and models list non-empty |
| 3 | `keprix --tui` with no provider opens TUI Setup Required panel (does not exit at CLI) |
| 4 | `/setup model` handoff runs subprocess and clears panel when provider configured |
| 5 | `/model` triggers setup handoff when unconfigured; cycles models when configured |
| 6 | First TUI message includes profile build offer once (directive in prompt path) |
| 7 | OpenClaw banner shows at most once per install |
| 8 | `pytest tests/setup/test_setup_status.py tests/tui/test_setup_handoff.py` passes |
| 9 | No duplicated wizard logic in TUI (handoff only) |
| 10 | Architecture reference status table updated |

---

## Dependencies

- Textual TUI shipped (prompts 201-206 parity series).
- `keprix setup` wizard complete (`setup.py`).
- Backend running for TUI (`keprix start`).

---

## Out of scope (defer)

- Ink/React `ui-tui` resurrection in-repo
- Inline API key entry widgets inside Textual (use subprocess wizard)
- Web `/onboarding` tour changes
- Telegram/Discord onboarding (already separate)

---

## Archive

Move to `prompts-archive/` when all AC pass. Update
`PROMPT-IMPLEMENTATION-AUDIT.md` and
`prompts-archive/ref-220-tui-first-run-onboarding-architecture-reference.md` status table.
