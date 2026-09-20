# Keprix agent handoff

## 2026-09-20: mutation-as-mount (773) pushed; Contabo owner-side

- **Git tip:** see latest `origin/main` after push (feature commit
  `feat(mutation): mount/unmount proposals via reversible lifecycle`)
- **Feature:** `keprix.mutation.mount` propose/approve/deny/reverse; four-eyes;
  Soft Wall/RLS/product-module bans; API `/api/mutation/mounts`
- **Local:** `pytest tests/mutation/test_mount_proposals.py` + recorded snapshots
- **Contabo deploy:** owner-side (this workstation does not rsync/SSH per AGENTS.md).
  Pull latest main, rsync, compose rebuild, verify app/api/marketing/`carinaai.uk` HTTP 200.
- **Prompts archived:** 768-773 under
  `archive/archived-prompts-library/keprix/keprix-dsh-idea-adoption/`
- **Docs:** `docs/architecture/mutation-as-mount.md`
- **Programme:** DSH idea adoption **complete**
