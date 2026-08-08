# Keprix - Prompt 220: TUI First-Run Onboarding Architecture Reference

## Purpose

Reference and dependency map for **first-install setup and onboarding** when a user runs
Keprix and launches the **Textual TUI** (`src/keprix/tui/`). Mirrors what Hermes Agent
did for CLI + Ink TUI, adapted to Keprix's HTTP TUI, existing `keprix setup` wizard,
and web workspace onboarding.

Build prompts **220-222** in numeric order. **Do not archive this file.**

---

## Hermes behavior (source of truth for parity)

Read-only reference tree:

`planning/competitor-research/agents-to-adopt/hermes-agent/`

| Hermes surface | What happens on first run |
| --- | --- |
| CLI chat / TUI launch | `_has_any_provider_configured()` in `hermes_cli/main.py`; prints guidance; offers `Run setup now? [Y/n]`; runs `hermes setup` or exits |
| Ink TUI (in-app) | Does **not** assume setup is done; shows **Setup Required** panel when no provider (`ui-tui/src/content/setup.ts`) |
| `/setup` slash | Suspends Ink UI, runs `hermes setup` subprocess (`setupHandoff.ts`, `slash/commands/setup.ts`), re-checks `setup.status` RPC |
| `/model` slash | In-TUI provider/model configuration (separate from full wizard) |
| First message | Gateway appends `profile_build_directive()` once (`agent/onboarding.py`) when `onboarding.profile_build: ask` |
| Contextual hints | One-time hints for busy input, tool progress, OpenClaw residue (`onboarding.seen.*` flags in `config.yaml`) |

Hermes did **not** use a blocking multi-page TUI questionnaire. Setup is CLI-driven;
the TUI handoff is the Keprix-relevant pattern.

---

## Product rule: all three surfaces, no user toggle

Onboarding is **not** a setting the user picks (CLI vs TUI vs web). The **entry surface**
decides which layer runs:

| Surface | Role | When it runs |
| --- | --- | --- |
| **CLI** (`keprix setup`) | **Canonical first-run wizard** | Fresh install, before chat/TUI; writes `config.yaml` + `.env` |
| **TUI** | **Minimal blocker only** | User skipped setup and launched TUI anyway; one-screen provider + model unblock |
| **Web** | **Operator checklist** | Instance already running; admin sees gaps (provider, channels, backup) |

No duplicate full wizards across surfaces. TUI does **not** replicate `SETUP_SECTIONS`.

## Keprix today (2026-07-06)

| Area | Status | Location |
| --- | --- | --- |
| CLI setup wizard (full) | **Shipped** | `keprix_cli/setup.py` (`run_setup_wizard`, `SETUP_SECTIONS`) |
| CLI first-run provider gate | **Shipped** | `keprix_cli/main.py` delegates to `setup/status.py`; TUI bypass when `--tui` |
| `keprix setup model` / `keprix model` | **Shipped** | `model_setup_flows.py`, shared with wizard |
| Contextual onboarding hints (library) | **Shipped** | `agent/onboarding.py` (busy input, tool progress, OpenClaw, profile build directive) |
| Profile build on first message | **Shipped** | `gateway/run.py` + `agent/onboarding_hooks.py` on HTTP chat path |
| Web onboarding checklist | **Shipped** | `support/onboarding.py`; auto-ticks `llm-provider` from setup status |
| Web first-run wizard | **Shipped** | `docs/getting-started/first-run.md`, setup API |
| Textual TUI chat | **Shipped** | `src/keprix/tui/app.py`, `client.py` |
| TUI setup-required state | **Shipped** | `tui/widgets/setup_required.py` |
| TUI minimal model picker | **Shipped** | Inline overlay + `POST /api/setup/minimal` |
| TUI `/setup` handoff (optional) | **Shipped** | `tui/setup_handoff.py`; fallback to full wizard |
| Setup status API for TUI | **Shipped** | `GET /api/setup/status` in `setup/routes.py` |
| CLI allows TUI without provider | **Shipped** | `KEPRIX_SETUP_REQUIRED=1`; Textual launch from `_launch_tui` |

---

## Target user journey (Keprix way)

```text
pip install keprix
        |
        v
keprix setup          <-- canonical path (full wizard, already shipped)
        |
        v
keprix start && keprix --tui
        |
        +-- provider configured --> normal TUI session
        |
        +-- provider NOT configured (user skipped setup) -->
              One-screen TUI blocker: pick provider, enter API key, save
              Optional: "Open full setup" runs `keprix setup` subprocess
              Do NOT hard-exit at CLI gate for --tui
        |
        v
Web admin (parallel track, not first-run)
        |
        support/onboarding checklist: LLM provider tick, channels, backup, etc.
```

**Principle:** CLI owns full configuration. TUI owns the **single blocker** that makes
chat impossible. Web owns **ongoing operator hygiene**, not install-time wizardry.

---

## API surface (target)

| Method | Route | Auth | Purpose |
| --- | --- | --- | --- |
| GET | `/api/setup/status` | optional (local dev) or session | `{ provider_configured, model_configured, active_provider, default_model, setup_sections, docs_url }` |
| GET | `/api/models/available` | session | existing; empty list when unconfigured |

Reuse `_has_any_provider_configured()` logic from `keprix_cli/main.py` via a shared
helper in `keprix/setup/status.py` (new) so CLI, API, and TUI agree.

---

## TUI surface (target)

| Component | Purpose |
| --- | --- |
| `SetupRequiredPanel` | Full-width overlay when `setup.status.provider_configured == false` |
| `run_setup_handoff()` | Suspend Textual app, subprocess `keprix setup [section]`, refresh status |
| Slash `/setup [section]` | Handoff to wizard (default section: `model`) |
| Slash `/model` (enhanced) | If unconfigured: handoff to `keprix setup model`; else cycle models |
| Startup banner | One-time OpenClaw residue hint via `detect_openclaw_residue()` |
| Status bar | Show `Setup required` vs `model: …` |

---

## Config keys (existing)

| Key | Default | Role |
| --- | --- | --- |
| `onboarding.profile_build` | `ask` | Offer opt-in profile build on first message |
| `onboarding.seen.*` | `{}` | One-time hint latches |
| `model.default` | (wizard sets) | Active model |
| `display.interface` | `cli` | Auto-TUI when `tui` |

---

## Build order (prompts 220-222)

```text
220 Setup status API + shared provider probe
  |
  v
221 TUI Setup Required panel + /setup handoff + soften CLI TUI gate
  |
  v
222 First-message onboarding (profile build + hints on TUI conversation path)
```

Prompt 220 has no TUI dependency. Prompt 221 depends on 220. Prompt 222 depends on
conversation POST path and can ship after 221.

---

## Non-goals

- Rebuilding the Ink/React `ui-tui` stack inside Keprix
- Replacing `keprix setup` with a duplicate wizard in Textual widgets
- Web `/onboarding` product tour (separate; link from setup panel only)
- Blocking questionnaire before any UI appears (Hermes never did this)

---

## Test commands (after implementation)

```bash
cd keprix
PYTHONPATH=src .venv/bin/python -m pytest tests/setup/test_setup_status.py -q
PYTHONPATH=src .venv/bin/python -m pytest tests/tui/test_setup_handoff.py -q
PYTHONPATH=src .venv/bin/python -m pytest tests/tui/test_onboarding_first_message.py -q
PYTHONPATH=src .venv/bin/python -m pytest tests/frontend/test_security_hub.py -q  # unchanged; sanity
```

---

## Related docs

- `docs/features/tui.md` (update parity matrix after 221)
- `docs/getting-started/first-run.md` (cross-link TUI path)
- `prompts-archive/ref-tui-hermes-parity-architecture.md` (behavior parity, not onboarding)
