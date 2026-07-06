---
name: ci-cd-pipeline
description: Build, test, lint, and deployment automation for FORGE.
version: 1.0.0
platforms: [linux, macos, windows]
metadata:
  keprix:
    tags: [forge, ci, cd, deploy, docker, build]
    related_skills: [keprix-core-developer]
---

# CI/CD Pipeline

FORGE build and deployment automation.

## Pipeline Stages

1. **Detect**; identify Docker, Python, Node, or Make targets
2. **Lint**; run detected lint command
3. **Test**; run pytest, npm test, or make test
4. **Build**; docker build, npm build, or make build
5. **Deploy**; generate deploy script or agent app bundle

## Target Detection

| Marker | Build strategy |
|--------|----------------|
| Dockerfile | `docker build` |
| package.json | `npm run build` |
| pyproject.toml | pytest + ruff |
| Makefile with `build:` | `make build` |

## Approval

Destructive deploy steps require human approval. FORGE generates scripts; it does not auto-push to production without explicit sign-off.
