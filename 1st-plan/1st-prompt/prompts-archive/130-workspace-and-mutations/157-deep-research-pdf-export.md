# Prompt 157: Deep Research deliverable export (PDF, HTML, DOCX)

## Problem

Deep research at `/research` produces good Markdown reports in the UI, but users cannot
package them as submission-ready PDFs or shareable documents. Navigating away and back
is now fixed (job persistence); the missing step is **export**.

Users expect something like Claude's research deliverables: clean typography, cover
metadata, downloadable PDF, optional Word copy for editors.

## Product decision (do not debate in implementation)

| Approach | Verdict |
| --- | --- |
| LLM outputs raw PDF bytes | **No.** Unreliable, huge tokens, not editable, hard to test. |
| LLM writes Markdown; server renders PDF | **Yes.** Matches existing Keprix export stack. |
| Optional LLM "polish" pass for submission tone | **Phase 2.** V1 is render-only from stored `report_markdown`. |

The research model's job stays: **structured Markdown with citations**. Rendering is a
deterministic export step, same pattern as workspace documents and Beacon delivery.

## Existing code to reuse (do not reinvent)

| Module | Use |
| --- | --- |
| `src/keprix/export/renderer.py` | `export_document()`, `markdown_to_html()`, cover/signatory injection |
| `src/keprix/export/pdf_engine.py` | WeasyPrint PDF (`render_pdf`) with plain-text fallback |
| `src/keprix/export/routes.py` | `/api/export/download` pattern for file response |
| `src/keprix/export/cover_page.py` | Cover page HTML (`generate_cover_html`) |
| `src/keprix/research/routes.py` | Add job-scoped export route next to `/report` |
| `src/keprix/research/store.py` | Job has `report_markdown`, `query`, `depth`, `sources`, `completed_at` |
| `src/keprix/research_workspace/reports/pandoc.py` | Optional DOCX via Pandoc when installed (graceful fallback) |

## Known gap to fix during this prompt

`export_document(..., format="pdf", include_cover=True)` builds HTML with a cover page,
but `render_pdf()` currently re-renders from raw Markdown and **drops the cover**. Fix
by adding `render_pdf_from_html(html: str) -> bytes` (or passing composed HTML through)
so PDF exports include cover, TOC styling, and signatory blocks when requested.

## Scope

### Backend

1. **`src/keprix/research/export.py`** (new)
   - `build_research_export_markdown(job: ResearchJob) -> str`
     - Strip internal HTML comment header if present (`<!-- keprix-research ... -->`).
     - Ensure title block: query, depth, date, source count.
   - `export_research_job(job, *, format, include_cover=True, prepared_by=None) -> dict`
     - Delegates to `export_document` for `pdf`, `html`, `markdown`.
     - For `docx`, try `research_workspace.reports.pandoc.render_with_pandoc`; return
       setup instructions if Pandoc missing (do not fail hard).
   - Default cover metadata:
     - `document_type`: "Deep Research Report"
     - `title`: first 80 chars of query
     - `document_id`: job id
     - `prepared_by`: from request body or user display name

2. **`src/keprix/research/routes.py`**
   - `GET /api/research/jobs/{job_id}/export?format=pdf|html|markdown|docx`
     - Auth: same as other research routes (`x-user-id` / session).
     - 404 if job missing; 409 if `report_markdown` not ready (still running).
     - Returns `FileResponse` or `Response` with `Content-Disposition: attachment`.
   - `POST /api/research/jobs/{job_id}/export` (optional body: `format`, `include_cover`,
     `prepared_by`, `classification`) for parity with `/api/export/download`.

3. **Styles**
   - Add `src/keprix/export/templates/research_report.css` (or extend `markdown_to_html`
     with a `template="research"` flag):
     - Serif body font, readable line length (~70ch), styled `h1`/`h2`, bullet spacing,
       citation superscript or bracket style, sources section with URL line breaks,
       page-break rules before major sections, print-friendly margins.
   - Wire template when exporting research jobs only (do not change all exports).

4. **Tests** (`tests/research/test_research_export.py`)
   - Export markdown returns 200 with same content (minus internal comment).
   - Export html returns `text/html` containing query string.
   - Export pdf returns `application/pdf` bytes starting with `%PDF` when WeasyPrint
     available; skip with reason if not installed in CI.
   - Running job returns 409.
   - Cover page HTML present in pdf/html path when `include_cover=true`.

### Frontend

1. **`frontend/src/lib/research-api.ts`**
   - `downloadResearchExport(jobId, format, options?)` opens or fetches blob URL.

2. **`frontend/src/app/(workspace)/research/page.tsx`**
   - When `report` is shown (or job status is terminal with report), show action row:
     - **Download PDF** (primary)
     - **Download Word** (if backend returns docx; show tooltip if fallback)
     - **Download HTML**
     - **Copy Markdown**
   - Disable buttons while job is running.
   - Show filename: `research-{slug}-{job_id}.pdf`.

3. **Docs** (`docs/features/research.md`)
   - Add Export section with formats and Pandoc/WeasyPrint optional deps.

## Out of scope (follow-on prompt 157b)

- Slide deck / presentation export (Marp or Pandoc beamer).
- LLM "executive brief" rewrite pass before export.
- Email delivery of PDF.
- Research workspace project export parity (already partially exists).

## Acceptance criteria

1. Completed deep research job has **Download PDF** on `/research` that saves a real PDF.
2. PDF includes cover page with query title, job id, generation date.
3. Body typography is clearly better than browser print-to-PDF of raw Markdown.
4. Export works after page reload / reconnect via `?job=rsch-...` (uses stored report).
5. No stub endpoints; tests cover happy path and not-ready job.
6. No em dashes or emojis in user-facing strings.

## Suggested test commands

```bash
cd /opt/lampp/htdocs/verlox/keprix
PYTHONPATH=src .venv/bin/pytest tests/research/test_research_export.py -q
PYTHONPATH=src .venv/bin/pytest tests/research/ -q
cd frontend && pnpm exec tsc --noEmit
```

## Phase 2 prompt stub (157b): Presentation export

If users want slides: add `format=slides` that runs a **short** LLM pass to produce
Marp-compatible Markdown (`---` slide breaks, title + 3 bullets per slide max), then
render to HTML slides or PDF via Pandoc/beamer. Still no binary PDF from the model.

## Optional synthesis prompt tweak (157c, not blocking)

Add to `synthesize_report()` in `src/keprix/research/synthesis.py` only if product
asks for "submission-ready" tone by default:

```text
Format for professional export: use ATX headings (##, ###), no HTML, put each source
on its own line in ## Sources with [n] Title - URL, avoid tables unless comparing
metrics, keep executive summary to 3-5 bullet points.
```

Do **not** ask the model to produce PDF, LaTeX, or base64.
