# Prompt 425 / 09: MkDocs links + env docs consistency pass

**Status: COMPLETED 2026-08-07**  
Series: Keprix public GTM + Hermes install parity  
Depends on: 423, 424  
Blocks: 426  
Writing style: plain ASCII only (no em/en dashes, no emoji).

## Purpose

Public docs must build and navigate without dead ends. Env docs must match
`.env.example` for the install story.

## Tasks

1. Run MkDocs build (or the repo's docs build script) and fix broken nav/links
   introduced or left open that affect getting-started and install.
2. Audit `docs/configuration/environment-variables.md` for:
   - Corrupted table rows
   - Install-critical vars documented: LLM keys, `KEPRIX_HOME`,
     `KEPRIX_INSTANCE_URL`, `KEPRIX_ALLOWED_ORIGINS`, auth flags
3. Ensure `.env.example` matches the documented minimum for Docker and CLI.
4. `docs/index.md`: install CTA points at the curl/primary path; homepage URL
   uses keprixai.com when referring to marketing site.
5. Confirm `repo_url` in `mkdocs.yml` matches the public GitHub URL.

## Acceptance

- [x] Docs build succeeds (or documented known MkDocs warnings only).
- [x] Getting-started links resolve.
- [x] Env docs and `.env.example` agree on required keys.

## What was built

- Fixed env table generator (corrupted Required/description bleed); install
  minimum section for LLM keys, `KEPRIX_HOME`, auth, origins, instance URL.
- `.env.example` documents `KEPRIX_HOME`; docs index curl CTA + keprixai.com.
- Docs generate uses writable `KEPRIX_DATA_DIR` under `/tmp` (no `/data` PermError).
- Fixed 3 MkDocs strict broken links (SECURITY/CHANGELOG root refs, missing
  opportunity release checklist).
- `repo_url` already `https://github.com/malike2356/keprix`.

## Verification

```bash
# Prefer project script if present
bash scripts/build-docs.sh 2>/dev/null || python -m mkdocs build --strict 2>&1 | tail -40
rg -n 'keprixai\\.com|curl -fsSL' docs/index.md
rg -n 'KEPRIX_HOME|ANTHROPIC_API_KEY|OPENAI_API_KEY' .env.example docs/configuration/environment-variables.md
```
