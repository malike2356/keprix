# Keprix prompts archive

Flat archive of shipped, superseded, and reference build prompts. No product subfolders.

## Rules

- Move a prompt here only when the requested modules, routes, tests, and docs exist (or the prompt is explicitly superseded).
- Keep active work in `../pending-prompts/`. Architecture maps live here as `ref-*.md` (see [ref-README.md](./ref-README.md)).
- Do not delete archived prompts; other docs may still reference them.

## Filename conventions

| Pattern | Meaning |
| --- | --- |
| `NNN-feature-name.md` | Completed Keprix build prompt |
| `NNN-*-verification.md` | Verification record for an archived prompt |
| `myapi-NN-*.md` | MyApi Open adoption series (archived) |
| `superseded-NN-*.md` | Delivered via Hermes clone foundation; do not re-run |
| `00*.md`, `270-*.md`, `*-pending-copy.md` | Orientation / blueprint copies kept for reference |
| `ref-*.md` | Architecture maps and build-order outlines (former `reference/` folder) |

## Index

See [INDEX.md](./INDEX.md) for the completed-prompt summary table.

Hermes-superseded notes: [superseded-by-hermes-clone-README.md](./superseded-by-hermes-clone-README.md).

MyApi series notes: [myapi-open-adoption-README.md](./myapi-open-adoption-README.md).

Architecture maps: [ref-README.md](./ref-README.md).
