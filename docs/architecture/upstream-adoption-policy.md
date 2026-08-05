# Upstream Adoption Policy

Keprix can adopt useful Hermes Agent changes without becoming a messy fork. The rule is simple: accept generic runtime improvements into core, keep Keprix product behavior in product layers, and translate names unless the original Hermes name is required for legal attribution, compatibility, or upstream tracking.

## Scope

This policy applies to patches, prompts, reports, and manual changes that come from the Hermes reference tree or from work that compares Keprix against Hermes behavior.

## Classification

Every upstream candidate must be classified before implementation.

| Class | Destination | Rule |
|---|---|---|
| Generic core improvement | `src/keprix/agent`, shared tools, provider routing, memory, sessions, retry, streaming | Can enter core when it is product neutral. |
| TUI improvement | `src/keprix/tui` and TUI tests | Can enter the Textual TUI when it preserves Keprix UX. Do not copy Hermes surface identity. |
| Product-layer change | Product modules, registries, hooks, billing, Channel Shield, Scout, Agent OS | Must stay outside core unless it is registered through the product hook or product prompt layer boundary. |
| Rename conflict | Any path or text introducing Hermes names | Translate through the rename inventory unless it is an upstream reference, migration fallback, or legal notice. |
| Packaging change | `pyproject.toml`, installers, Docker, Nix, desktop wrappers | Must preserve the `keprix` entry point and packaged install behavior. |

## Intake Checklist

Before applying an upstream patch, answer these questions in the implementation note or prompt:

- Has an operator run `keprix upstream decide` (or Admin > Hermes upstream) for this feature?
- Does this modify core runtime behavior?
- Does this modify a product layer or product-specific policy?
- Does this introduce Hermes names into user-facing Keprix copy?
- Does this affect install packaging or entry points?
- Does this affect TUI behavior or visual identity?
- Does this need a compatibility fallback for `.hermes`, `HERMES_*`, or old state paths?
- Which tests prove the change belongs where it was placed?
- Did parity gates pass, and was `keprix upstream complete` recorded?

## Control plane commands

```bash
keprix upstream check
keprix upstream review
keprix upstream decide <id> --status adopt_with_hardening
keprix upstream adopt <id>
keprix upstream complete <id> --equivalent <capability-id>
```

See [Hermes upstream monitor](../operations/upstream-monitor.md).

## Prompt Requirements

Generated adoption prompts must tell agents where the change belongs:

- Put generic runtime fixes in core.
- Put product-specific behavior behind product hooks, product prompt layers, ACLs, or the relevant product package.
- Put upstream comparison, monitoring, and legal attribution in docs or upstream tracking modules.
- Translate names through `docs/architecture/hermes-to-keprix-rename-inventory.md`.
- Reference `docs/architecture/core-product-boundary.md` when the change touches shared runtime code.

## Compatibility

Keprix primary state is `.keprix`. Legacy `.hermes` paths and `HERMES_*` variables can be read as migration fallbacks, but new writes should use Keprix names.

Hermes remains a valid name only when the object is the upstream reference project, a legal attribution, an old compatibility path, or an adoption-monitoring artifact.

## Verification

Use these checks for upstream adoption work:

```bash
keprix upstream --help
python -m pytest tests/upstream tests/upgrade tests/cli -q
python -m pytest tests/architecture -q
```

If a check fails because a local service, fixture, or optional dependency is unavailable, document the exact failure and the next action in the adoption report.
