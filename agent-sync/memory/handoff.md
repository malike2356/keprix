# Keprix agent handoff

## 2026-09-20: reversible plugin lifecycle (769) pushed; Contabo owner-side

- **Git tip (after push):** see latest `origin/main`
- **Feature:** reversible plugin lifecycle (`keprix.plugin_lifecycle`); hot
  `keprix plugins enable|disable` mount/unmount; ledger undoes tools, prompt
  sections, MCP, seam Providers
- **Prior:** capability seams `eee61cf` / docs handoff
- **Local:** `pytest src/keprix/tests/plugin_lifecycle/test_reversible_lifecycle.py src/keprix/tests/seams/test_capability_seams.py` (14 passed)
- **Contabo deploy:** owner-side (this workstation does not rsync/SSH per AGENTS.md).
  Pull latest main, rsync, compose rebuild, verify app/api/marketing/`carinaai.uk` HTTP 200.
- **Prompts archived:** 768 + 769 under
  `archive/archived-prompts-library/keprix/keprix-dsh-idea-adoption/`
- **Docs:** `docs/architecture/reversible-plugin-lifecycle.md`
