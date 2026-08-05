# Obsidian Vault Starter

Use this skill when the operator wants Keprix and Obsidian to share a markdown vault.

## When To Use

- Initialize a new vault with Keprix folder conventions.
- Explain where agents should write inbox notes, project notes, resources, and archived material.
- Connect vault workflows to `llm-wiki`, research exports, and Keprix session exports.

## Commands

```bash
keprix vault list-packs
keprix vault init --pack obsidian-starter --path ~/vault
keprix vault validate --path ~/vault
```

The pack writes `KEPRIX.md`, a PARA-style folder tree, note templates, and `.keprix/vault-manifest.json`.
