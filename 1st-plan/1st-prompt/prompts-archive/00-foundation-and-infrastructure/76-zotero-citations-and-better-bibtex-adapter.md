# keprix - Prompt 76: Zotero Citations and Better BibTeX Adapter

> **Status (2026-07-05):** Implemented `src/keprix/research_workspace/citations/` (Zotero web/local clients, BibTeX/BBT import, CSL export, literature notes, bibliography), `/api/research/zotero/*`, Zotero UI panels, `docs/research/zotero-citation-adapter.md`, and 9 new tests (28 total in `tests/research_workspace/`).

## Context

keprix needs a citation brain for research workflows. Zotero should be the primary reference manager integration. Better BibTeX should be supported for stable citation keys and text-based writing workflows.

## Working Directory

`/opt/lampp/htdocs/verlox/keprix/keprix/`

## Files To Create

```text
backend/research_workspace/citations/
  __init__.py
  zotero_api.py
  zotero_local.py
  better_bibtex.py
  bibtex.py
  csl.py
  citation_keys.py
  bibliography.py
  literature_notes.py
frontend/src/components/research/ZoteroSettings.tsx
frontend/src/components/research/CitationPicker.tsx
tests/research_workspace/test_zotero_api.py
tests/research_workspace/test_bibtex.py
tests/research_workspace/test_literature_notes.py
docs/research/zotero-citation-adapter.md
```

## Required Features

### Zotero Modes

Support:

- Zotero Web API.
- Zotero local API when running on the user's machine.
- BibTeX file import.
- Better BibTeX export import.

### Citation Objects

Normalize references into:

- Item key.
- Citation key.
- Title.
- Authors.
- Year.
- Publication.
- DOI.
- URL.
- Abstract.
- Tags.
- Collections.
- Attachments.
- Notes.

### Literature Notes

Generate literature notes with:

- Citation metadata.
- Summary.
- Key claims.
- Methods.
- Findings.
- Limitations.
- Relevance to project.
- Linked Obsidian note path if configured.

### Bibliography Export

Support:

- BibTeX.
- CSL JSON.
- Markdown references.
- Report-ready bibliography section.

## Security And Privacy

- Store Zotero API keys in the vault.
- Do not upload private attachments to remote services without approval.
- Respect group library permissions.

## Acceptance Criteria

- User can connect a Zotero library.
- User can import a Better BibTeX file.
- keprix can create literature notes from selected items.
- Reports can include citations and bibliography.
- Citation keys remain stable across exports when Better BibTeX data is available.
