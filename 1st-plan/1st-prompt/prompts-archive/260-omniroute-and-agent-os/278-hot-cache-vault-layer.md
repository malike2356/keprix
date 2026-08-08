# Keprix - Prompt 278: Hot cache vault layer

**Series:** Nate Herk AIOS adoption **274-279**  
**Master reference:** `../prompts-archive/ref-273-nate-herk-aios-adoption-master-reference.md`  
**Depends on:** **258**, `llm-wiki` skill  
**Working directory:** `/opt/lampp/htdocs/verlox/keprix/`

---

## 1. What this prompt builds

**Hot cache vault layer** (`wiki/hot.md`): optional ~500-token rolling summary of recent session context for executive-assistant style workspaces (Nate Herk pattern). Reduces full wiki crawls; complements existing `llm-wiki` index/log orientation.

**Read order (document in KEPRIX.md):**

1. `wiki/hot.md` (if present)
2. `wiki/index.md`
3. Recent `wiki/log.md`
4. Target wiki pages

**Non-goals:**

- Mandatory hot cache for all workspaces
- Replacing episodic memory or RAG
- Karpathy layout mandate (optional preset flag only)

---

## 2. Already built

| Area | Location |
| --- | --- |
| llm-wiki skill | `skills/research/llm-wiki/SKILL.md` |
| Workspace memory | **258** |
| Session store | SessionDB |

---

## 3. Architecture

```text
Session end / significant turn hook
        |
        v
hot_cache_service.py
  - summarize recent turns (LLM or heuristic v1)
  - cap ~500 tokens
  - write wiki/hot.md
        |
        v
Agent read path (llm-wiki + KEPRIX.md)
```

Config per workspace: `hot_cache.enabled` (default false; true for `executive_assistant` preset).

---

## 4. `hot.md` format

```markdown
# Hot cache

> Rolling context (~500 tokens). Auto-updated. Do not manually edit unless correcting errors.

**Last updated:** 2026-07-09T21:00:00Z
**Source session:** sess_abc123

## Recent focus
- Q2 launch priorities; waiting on speaker lineup
- ...

## Open threads
- ...
```

---

## 5. Preset: `executive_assistant`

Add to **258** template presets:

```text
workspace/
  context/          # from 276
  raw/
  wiki/
    hot.md          # seeded empty
    index.md
    log.md
  outputs/
  KEPRIX.md
```

`KEPRIX.md` section: when to read hot vs full wiki (mirror Nate EA rules).

---

## 6. API routes

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/api/workspaces/{id}/hot-cache/refresh` | Force update |
| GET | `/api/workspaces/{id}/hot-cache` | Current content |
| PUT | `/api/workspaces/{id}/hot-cache/config` | `{ enabled: bool }` |

Hook: call `refresh` on session idle timeout (debounced 5 min).

---

## 7. llm-wiki skill amendment

Add section to `llm-wiki/SKILL.md`:

- If `$WIKI/hot.md` exists and `enabled`, read before index
- After ingest/lint, optionally refresh hot cache
- YouTube/research vaults may leave hot disabled

No fork of skill repo; patch in place.

---

## 8. Files to create

```
src/keprix/workspace/
  hot_cache_service.py
  hot_cache_config.py

src/keprix/api/
  hot_cache_routes.py

docs/features/hot-cache-vault-layer.md

tests/workspace/
  test_hot_cache_service.py
  test_hot_cache_routes.py
```

Amend **258** preset list + `keprix_md_generator.py` hot section.

---

## 9. Acceptance criteria

- Disabled workspace: no `hot.md` writes; read path skips hot.
- Enabled workspace: refresh produces file <= 600 tokens (test with fixture summary).
- `llm-wiki` orientation docs mention hot read order.
- Executive assistant preset enables hot by default.
- Manual refresh API returns updated timestamp.
- Tests mock LLM summarizer; heuristic fallback works without API key.

---

## 10. Dependencies

- **Amend:** **258**, `llm-wiki/SKILL.md`
- **Optional:** **276** context files inform hot summary
