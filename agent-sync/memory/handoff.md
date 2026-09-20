# Keprix agent handoff

## 2026-09-20: capability presets (771) pushed; Contabo owner-side

- **Git tip (after push):** see latest `origin/main`
- **Feature:** declarative capability packs (`coding`, `crm`, `sidecar`) in
  `keprix.capability_presets`; apply via 769; CLI `keprix presets`;
  API `/api/capability-presets`
- **Local:** `pytest src/keprix/tests/capability_presets/test_capability_presets.py` (11 passed)
- **Contabo deploy:** owner-side (this workstation does not rsync/SSH per AGENTS.md).
  Pull latest main, rsync, compose rebuild, verify app/api/marketing/`carinaai.uk` HTTP 200.
- **Prompts archived:** 768-771 under
  `archive/archived-prompts-library/keprix/keprix-dsh-idea-adoption/`
- **Docs:** `docs/architecture/capability-presets.md`
