# Agent brief: Prompt 117 marketing landing verification

**Status:** Archived in `prompts-archive/117-marketing-landing-page.md`  
**Reconciled:** 2026-07-05 (all acceptance items confirmed)  
**Working directory:** `/opt/lampp/htdocs/verlox/keprix/frontend/`  
**Goal:** Confirm the Next.js marketing surface is complete; fix any gaps; no stubs.

## Context

Prompt 117 is archived. Most acceptance criteria are implemented. This brief is a
focused verification and cleanup pass before treating 117 as closed.

## Already done (do not redo)

- `(marketing)/` layout with Navbar, Footer, 8 home sections
- Hero terminal animation, tagline "Ten agents. One OS." in Hero + metadata
- `/pricing`, `/changelog`, `/legal/privacy`, `/legal/terms`
- Dark theme via `keprix-theme.ts`
- Footer legal links point to `/legal/privacy` and `/legal/terms` (not `#`)

## Remaining gaps to fix

| Item | File | Action |
| --- | --- | --- |
| Discord/Telegram placeholder links | `src/components/marketing/Footer.tsx` | Replace `#` with real URLs or remove rows until channels exist |
| `/docs` route | `src/app/(marketing)/` | Add page or redirect to `docs/` / GitHub docs; Footer links to `/docs` |
| Changelog source | `src/app/(marketing)/changelog/page.tsx` | Wire to root `CHANGELOG.md` when present; keep static copy if file missing |
| Mobile nav | `src/components/marketing/Navbar.tsx` | Verify hamburger below 768px |
| Build gate | `frontend/` | Run `pnpm build` and fix any TypeScript or lint errors |

## Verification commands

```bash
cd /opt/lampp/htdocs/verlox/keprix/frontend
pnpm build
pnpm lint  # if configured

# Grep guards (must return empty in marketing components)
rg -i 'lorem|saasable|flexy demo|coming soon' src/components/marketing src/app/\(marketing\)
```

## Acceptance checklist

- [x] `http://localhost:3000` renders all sections with Keprix copy
- [x] Zero placeholder "Lorem ipsum" or upstream demo brand names
- [x] Navbar collapses on mobile
- [x] CTAs link to `/auth/setup` and GitHub repo
- [x] No `#` hrefs in Footer
- [x] `pnpm build` passes

## Out of scope

- Static site at `marketing/sites/keprix/` (Prompt 115, completed)
- Workspace or admin routes (Prompts 118, 136, 137)
