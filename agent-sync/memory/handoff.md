# Keprix agent handoff

## 2026-09-20: capability seams (768) pushed; Contabo owner-side

- **Git SHA:** `eee61cf` on `origin/main`
- **Subject:** feat(seams): add capability seams (Definition/Provider/Consumer)
- **Local:** `pytest src/keprix/tests/seams/test_capability_seams.py` (9 passed)
- **Contabo deploy:** owner-side (this workstation does not rsync/SSH per AGENTS.md). Pull `eee61cf`, rsync, compose rebuild, then verify app/api/marketing/`carinaai.uk` HTTP 200.
- **Prompt:** 768 archived under `archive/archived-prompts-library/keprix/keprix-dsh-idea-adoption/768-capability-seams.md`
- **Docs:** `docs/architecture/capability-seams.md`
