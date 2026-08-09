# Self-knowledge (RAG) troubleshooting

Keprix indexes a curated product corpus under user `__keprix_self__` so chat and operator copilots can answer "what can Keprix do?" without inventing features.

## Re-index (operators)

```bash
keprix memory index-self
keprix memory search-self "outreach soft wall"
```

Or HTTP (authenticated admin/operator as configured):

- `POST /api/rag/self-knowledge/index`
- `POST /api/rag/self-knowledge/search`

API bootstrap runs ingest when `KEPRIX_SELF_KNOWLEDGE_BOOTSTRAP=true` (default).

## Symptom: Answers miss CRM, outreach, Companies House, or sidecars

**Fix:** Deploy docs that include those guides, then re-run `keprix memory index-self`. Curated paths live in `src/keprix/memory/rag/self_knowledge.py` (`_SELF_DOC_PATHS`).

## Symptom: Answers invent menus that do not exist

**Fix:** Prefer retrieved self-knowledge over model guesswork; re-index after nav changes. File a bug if a live module is missing from the GUI catalog.
