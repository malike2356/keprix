# Skill packs

Hub packs bundle skills, templates, and connectors with signed manifests.

## Layout

Packages live under `packages/packs/`, `packages/templates/`, and `packages/connectors/`.

## Manifest

Each pack includes `manifest.json` with name, version, permissions, and signature.

## Install

```bash
curl -X POST http://127.0.0.1:3333/api/hub/install \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"name": "example-pack", "approved": true}'
```

Or use the `/hub` UI.

## Submitting packs

1. Fork the repository
2. Add your pack under `packages/`
3. Sign the manifest per hub verifier rules
4. Open a PR with tests and changelog entry

Regulated workspaces may require clinical pack gate sign-off (Prompt 112).
