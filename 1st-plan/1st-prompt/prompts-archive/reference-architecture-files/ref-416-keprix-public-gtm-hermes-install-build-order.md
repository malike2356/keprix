# Ref 416: Public GTM + Hermes install parity build order

## Goal

Make Keprix **public GTM ready**: separate Verlox workspace noise from the
product tree strangers clone, refresh documentation, and match Hermes-class
end-user install UX (one working public install path, then a usable agent).

This pack **supersedes** private-only scope of ref-365 for *public* launch work.
Do **not** redo TUI behavior parity (341-349) or private ship gate (365-370)
unless a check regresses; re-run those gates as evidence, do not rebuild them.

Hermes reference (external): `https://github.com/NousResearch/hermes-agent`
and docs install one-liner pattern (`curl …/install.sh | bash`, clone under
`~/.hermes/hermes-agent`, `hermes` on PATH, then setup/chat).

## Why now (facts as of 2026-08-07)

1. Anonymous `https://github.com/malike2356/keprix` returns **404** (private or
   unpublished). Marketing and README clone URLs do not work for outsiders.
2. `pipx install 'keprix[tui]'` from PyPI is **404**; docs claim a path users
   cannot run.
3. `scripts/install-curl.sh` pipes raw GitHub `install.sh`, which is also 404.
4. Landing copy still shows incomplete `git clone github.com/malike2356/keprix`
   and stale `keprixai.uk` metadata; owner domain is **`keprixai.com`**.
5. Workspace tree still mixes product code with planning noise (`1st-plan/`),
   local data (`keprix-data/`), and Verlox-only notes. Private ship (365) moved
   competitor research out; public GTM needs a stricter ship face.

## Execution order

| Prompt | Title | Depends on |
| --- | --- | --- |
| 416 | Overview, inventory, Hermes gap map | none |
| 417 | Quarantine workspace noise from ship face | 416 |
| 418 | Public git hygiene (ignore, export-ignore, root layout) | 417 |
| 419 | Hermes-parity curl installer + `keprix setup` first run | 418 |
| 420 | Docker Compose full-stack path as secondary, honest docs | 419 |
| 421 | PyPI / pipx honesty and release package path | 418 |
| 422 | README + CONTRIBUTING rewrite (install-first) | 419, 421 |
| 423 | Getting-started docs refresh (install, quickstart, first-run) | 422 |
| 424 | Marketing + metadata domain flip to keprixai.com | 416 |
| 425 | MkDocs / docs link + env docs consistency pass | 423, 424 |
| 426 | Public GTM ship gate script + CI hook | 419, 420, 421, 425 |
| 427 | Public origin notes (Cloudflare + Contabo nginx marketing FE) | 424 |
| 428 | Public GTM sign-off and launch checklist | 426, 427 |

## Non-goals

- Rebuilding TUI Hermes *behavior* parity (already gated 100/100).
- New Stripe prices or paid SaaS legal entity fill.
- Nesting `carina/verlox/` or pulling Carina tree into Keprix.
- Deleting production data, secrets, or `.access/` credentials.
- Full Contabo Keprix API stack deploy (optional follow-up; 427 is marketing
  origin + docs only unless owner expands scope).
- Making `1st-plan/` vanish from the *workspace*; it must leave the *public
  ship face* (export-ignore / archive / documented local-only).

## Definition of done

1. A stranger with GitHub access can install via a documented one-liner that
   works against the **public** repo (or documented interim if owner delays
   publicize; gate must fail closed until public).
2. After install: `keprix --version` and either `keprix` / `keprix tui` or
   documented Docker UI URL works without activating a contributor venv.
3. README leads with install, not internal workspace paths.
4. No `keprixai.uk` in first-party product/docs/marketing (domain is
   `keprixai.com`).
5. Workspace planning noise is not in the public clone story.
6. `bash scripts/check-public-gtm-gate.sh` passes.
7. Sign-off doc lists remaining honest risks (legal, email DNS, PyPI status).

## Related archives

- `ref-365-private-oss-ship-ready-build-order.md` (private soft ship)
- `docs/architecture/private-ship-signoff.md`
- `ref-341-tui-100-percent-hermes-parity-build-order.md` (TUI behavior)
- `ref-317-keprix-hermes-core-alignment-build-order.md` (agent alignment)
