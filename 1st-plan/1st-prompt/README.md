# Keprix Build Prompts

This directory is the control surface for the Keprix prompt library.

## Where Prompts Live

| Path | Purpose |
| --- | --- |
| `pending-prompts/` | **Build queue only**: numbered implementation prompts ready to execute (empty; add next prompt here). |
| `prompts-archive/ref-*.md` | Wiring outlines and architecture maps (not executable prompts). |
| `prompts-archive/` | Completed, superseded, deprecated, or moved prompts. |
| `00a-product-vision-and-agent-consolidation-map.md` | Product vision and boundary map. |
| `00b-full-build-scope-and-build-order.md` | Full build scope and build-order guide. |
| `PROMPT-CROSSREF-GUIDE.md` | Numbering and dependency reference for agents. |
| `PROMPT-IMPLEMENTATION-AUDIT.md` | Shipped status, deferred AC, and test commands. |

## Execution Rule

Build in numeric order. Do not skip a capability because older notes called it
future work. Once a prompt is fully implemented and verified, move it out of
`pending-prompts/` and into `prompts-archive/`.

## No Stubs Rule (hard constraint for all agents)

When you take a prompt from `pending-prompts/`, you must ship it **fully** before
moving on:

1. **No stubs.** Do not leave `pass`, fake returns, "coming soon" messages,
   simulated endpoints, or TODO placeholders in the shipped code path for that
   prompt.
2. **No deferred wiring.** If a slash command, API route, CLI subcommand, or UI
   action is in scope, wire it to the real module (store, job runner, tool
   registry, config setter, etc.). Optional third-party backends (E2B, Modal) may
   fall back to Docker when credentials are missing; they must still run real
   code, not return a static error without trying the fallback.
3. **Archive only when done.** Move the prompt file to
   `prompts-archive/` only after acceptance criteria are met, tests
   pass, and a grep for stub markers in the new modules is clean.
4. **Update the audit.** Add the prompt to `PROMPT-IMPLEMENTATION-AUDIT.md`
   and `prompts-archive/README.md` when archived.
5. **Next prompt only after completion.** Do not start the next pending prompt
   while the current one still has placeholder behavior in production paths.

Allowed exceptions: abstract base classes with `NotImplementedError`, test doubles,
and Hermes upstream code outside the Keprix prompt scope.

## Current queue

`pending-prompts/` holds **224-228** (built apps navigation, 2026-07-07). Reference **223**. See `pending-prompts/README.md`.

Prior series through **222** archived under `prompts-archive/`.

Series reference maps (for dependency lookup only):

```text
prompts-archive/ref-138-chat-mutation-e2e-wiring-outline.md
prompts-archive/ref-144-llm-usage-analytics-wiring-outline.md
prompts-archive/ref-149-mutation-engine-architecture-reference.md
```

Pick the next capability from `PROMPT-IMPLEMENTATION-AUDIT.md` deferred AC sections,
the product backlog, or add a new numbered prompt to `pending-prompts/`.

Archived root control copies also live under `prompts-archive/` (including
`00-project-setup-architecture-and-developer-access.md`).

## Product Boundaries

- Keprix core is general-purpose AI agent infrastructure.
- Petraclus owns cybersecurity, offensive tooling, case authorization, forensics, SIEM, and threat intelligence.
- AbbiS owns borehole business workflows and product-specific Ghana localization.
- Scout remains a separate paid governance connector.
- Carina and Aiva remain commercial products, not Keprix core.
