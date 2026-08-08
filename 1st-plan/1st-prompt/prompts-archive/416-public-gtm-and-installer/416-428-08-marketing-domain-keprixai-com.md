# Prompt 424 / 08: Marketing + metadata domain flip to keprixai.com

**Status: COMPLETED 2026-08-07**  
Series: Keprix public GTM + Hermes install parity  
Depends on: 416  
Blocks: 425, 427  
Writing style: plain ASCII only (no em/en dashes, no emoji).

## Purpose

Align all product/marketing/public metadata with the owned domain
**`keprixai.com`**. Remove stale wrong-domain placeholders.

## Tasks

1. Update `frontend/src/app/(marketing)/layout.tsx` `metadataBase` to
   `https://keprixai.com`.
2. Fix marketing install snippets (`HowItWorks` and any twins):
   - Complete `https://github.com/malike2356/keprix.git` clone URL, **or**
   - Prefer the curl one-liner as step 01 if that is GTM primary.
3. Grep and replace first-party references:
   ```bash
   rg -n 'keprixai\\.uk' --glob '!**/node_modules/**' --glob '!**/.next/**' --glob '!**/1st-plan/prompts-archive/**'
   ```
   Update product code, docs, config constants, and marketing. Leave historical
   archive prompt text unless it confuses active docs; prefer a note in gap map.
4. Update self-knowledge / constants GitHub + site URLs if they advertise a
   public homepage.
5. Do not invent email DNS records; email warning on Cloudflare can remain
   until a mail provider is chosen (note in 428).

## Acceptance

- [x] Zero wrong-domain placeholders in frontend marketing and `docs/` (archive
      historical prompts may still mention the old name).
- [x] `metadataBase` is `https://keprixai.com`.
- [x] Marketing clone/curl commands are copy-paste valid.

## What was built

- `metadataBase` -> `https://keprixai.com`.
- `config/billing.yaml` website, `constants.HOMEPAGE` / `DOCS_URL`, support
  article docs links, self-knowledge Homepage line.
- HowItWorks already curl-first; docs marketing INSTALL_CMD already full clone URL.
- `related-projects.md` Keprix website -> keprixai.com.
- private-ship-signoff risk line updated; gap map 424 DONE; origin still 427.

## Verification

```bash
rg -n 'keprixai\\.uk' frontend/src docs README.md mkdocs.yml || true
rg -n 'metadataBase|keprixai\\.com' frontend/src/app/\(marketing\)/layout.tsx
rg -n 'git clone https://|curl -fsSL' frontend/src/components/marketing/HowItWorks.tsx
```
