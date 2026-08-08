# Prompt 575: Marketing hero CTA self-host vs hosted

**Status:** SUPERSEDED 2026-08-08 by prompts 600-618
**Series:** Keprix public GTM hard-ready (570-582)  
**Depends on:** 570, 571  
**Blocks:** 582  
**Writing style:** plain ASCII only.

## Purpose

Soft GTM noted primary hero CTA may send strangers to `/auth/setup` (hosted
signup) instead of self-host install. Hard GTM must make Community self-host
obvious without lying about Contabo hosted app.

## Tasks

1. Inspect live `https://keprixai.com/` hero CTAs and secondary links.
2. Decide copy model (document):
   - Primary: Install Community (links to `/docs/...` or `#install` with curl).
   - Secondary: Use hosted app (`https://app.keprixai.com/` or marketing auth).
3. Implement in marketing frontend source of truth (not only Contabo static
   if Contabo is a deploy target of that FE).
4. Ensure download/install page does **not** claim `.deb` / AppImage / dmg unless
   578 ships them.
5. After Contabo marketing deploy: verify `https://carinaai.uk/` still 200.

## Acceptance

- [ ] Stranger can reach curl install from homepage in one click without signup.
- [ ] Hosted path still available but not the only story.
- [ ] No fake binary download buttons.

## Verification

```bash
curl -fsS -o /dev/null -w '%{http_code}\n' https://keprixai.com/
curl -fsS -o /dev/null -w '%{http_code}\n' https://carinaai.uk/
# Manual: hero primary label + href match install docs
```
