# Documentation source

Markdown for the public docs site lives in this directory.

MkDocs configuration is at the repository root: [`mkdocs.yml`](../mkdocs.yml).

```bash
bash scripts/build-docs.sh   # generate reference pages + build site/
bash scripts/serve-docs.sh   # local preview
```

Build output: `frontend/public/guide/` (served at `/guide/` by the Next.js app).

```bash
bash scripts/build-docs.sh   # generate reference pages + build guide/
bash scripts/serve-docs.sh   # optional: standalone MkDocs preview on :8000
```

## Architecture

Start with [Core and product boundary](architecture/core-product-boundary.md) before changing agent runtime, TUI, tools, memory, provider routing, product modules, or admin surfaces.

## Contact

Verlox Ltd: [contact@verlox.uk](mailto:contact@verlox.uk)
