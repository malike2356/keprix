# keprix - Prompt 115: Standalone Marketing Site Build, Deploy, And Analytics

## Purpose

Implement keprix's standalone marketing site using the content direction from
Prompt 134.

This prompt builds the actual static site, deploy workflow, analytics hooks,
SEO files, and validation checks.

## Working Directory

```text
/opt/lampp/htdocs/verlox/keprix/marketing/sites/keprix/
```

Create this directory if missing.

## Technology

Use a static-first implementation.

Preferred:

- Astro or Eleventy if package tooling exists in this workspace.
- Plain HTML, CSS, and small vanilla JS if no package tooling is present.

Do not add a heavy app framework just for a marketing site.

## Required Files

Create:

```text
marketing/sites/keprix/
  README.md
  package.json                  # only if a build tool is used
  src/                          # only if a build tool is used
  public/                       # static assets
  dist/                         # build output, ignored if generated
  index.html                    # if plain static
  architecture/index.html
  consolidation/index.html
  mutation-engine/index.html
  playbooks/index.html
  hub/index.html
  community/index.html
  contributing/index.html
  security/index.html
  roadmap/index.html
  brand-boundary/index.html
  legal/index.html
  assets/
    css/site.css
    js/site.js
  robots.txt
  sitemap.xml
```

## Config

Create a site config file:

```text
marketing/sites/keprix/site.config.json
```

It must include:

```json
{
  "siteName": "keprix",
  "tagline": "Ten agents. One OS.",
  "domain": "https://keprixai.uk",
  "repoUrl": "https://github.com/malike2356/keprix",
  "docsUrl": "https://github.com/malike2356/keprix",
  "sponsorText": "Sponsored by Carina",
  "scoutUrl": "https://labyrinthscout.com",
  "consolidationCapabilityCount": 10
}
```

The code must read repeated links and labels from this config instead of
hardcoding them in every page.

## Design Requirements

Use a professional open-source product interface:

- Header with logo text `keprix`
- Nav: Docs, Architecture, Consolidation, Playbooks, Hub, Community, GitHub
- Hero with terminal or workspace visual
- Dark and light sections
- Code blocks for install commands
- Architecture diagram built with HTML/CSS, not image-only text
- Mobile responsive layout
- No nested cards
- No hero card
- Cards only for repeated capability items
- Stable button dimensions
- No text overflow on mobile
- No emojis
- No forbidden dash characters

## Required Homepage Copy

Use this exact hero structure unless the brand file has been updated:

```text
H1: keprix
Subheadline: Ten agents. One OS. The open-source AI agent platform for building AI products.
Body: One installable workspace with memory, tools, channels, playbooks, and a Mutation
engine that builds new capabilities after your approval.
Primary CTA: Get started on GitHub
Secondary CTA: Read the docs
Tertiary link: See what it consolidates -> /consolidation/
```

### Consolidation page (`consolidation/index.html`)

Implement per Prompt 134 section `/consolidation/`:

- Page title: `Ten agents. One OS. | keprix`
- H1: `Ten agents. One OS.`
- Capability grid (10 rows, labels only; no upstream repo names)
- Short Mutation engine callout
- Short Scout optional connector callout with link to labyrinthscout.com
- CTA: Get started on GitHub

Build the grid with semantic HTML (`<section>`, `<ul>`, or a definition list). No
comparison table naming competitors.

Footer sponsor line:

```text
Sponsored by Carina.
```

Do not use sponsor wording in the H1, nav, page title, package name, repo name,
or metadata title.

## Install Copy

Until the package is published, use placeholders marked clearly:

```text
git clone https://github.com/malike2356/keprix
cd keprix
docker compose up
```

Do not mention `carina-keprix`, `pip install carina-keprix`, or old package names.

## Legal And Community Pages

Add:

- MIT licence summary page that links to the repository licence.
- Security reporting page with responsible disclosure instructions.
- Code of Conduct page or link.
- Brand boundary page summarising that keprix is standalone and sponsored by
  Carina only.

## Analytics

Use privacy-respecting analytics only.

Allowed:

- Plausible
- Umami
- Server log analytics

Not allowed without a separate consent banner:

- Google Analytics
- Meta Pixel
- LinkedIn Insight Tag
- Any retargeting script

Analytics must be configurable:

```text
keprix_ANALYTICS_PROVIDER=none
keprix_ANALYTICS_DOMAIN=keprixai.uk
```

Default must be `none`.

## Deploy Script

Create:

```text
marketing/sites/keprix/scripts/deploy.sh
```

The script must:

1. Build the site if a build tool is used.
2. Validate no forbidden brand strings exist.
3. Validate no forbidden dash or emoji characters exist.
4. Rsync to a configurable remote path.
5. Not require any Carina deploy script.

Environment variables:

```text
keprix_DEPLOY_TARGET=aman
keprix_DEPLOY_PATH=/www/wwwroot/keprixai.uk
keprix_DEPLOY_KEY=$HOME/.ssh/id_ed25519
```

## Validation Script

Create:

```text
marketing/sites/keprix/scripts/validate-site.sh
```

It must fail if it finds:

- `Carina keprix`
- `Powered by Carina`
- `Carina Aiva`
- `Aiva`
- `carina-keprix`
- `Petraclus` in product-family context
- Upstream agent repo names in public HTML body text (Hermes, OpenClaw, Odysseus, LangGraph, CrewAI, AutoGen, LaVague, TaskWeaver, SWE-agent)
- em dash
- en dash
- emojis

It must allow:

- `Sponsored by Carina`
- `Labyrinth Scout` as optional connector

## Redirect Guidance

If old URLs ever existed under `carinaai.uk`, document redirect strategy in:

```text
marketing/sites/keprix/REDIRECTS.md
```

Recommended:

- `carinaai.uk/keprix/` should not be treated as canonical.
- Canonical should be `https://keprixai.uk/`.
- If redirects are configured, use 301 from old Carina paths to the standalone
  keprix domain.

Do not add redirects inside Carina source in this prompt.

## Acceptance Criteria

- The site builds or opens as static HTML.
- `scripts/validate-site.sh` passes.
- The homepage has no Carina product-family language.
- Hero subheadline includes `Ten agents. One OS.`
- `/consolidation/` page exists and passes validate-site.sh.
- keprix is standalone in title, metadata, nav, and footer.
- Sponsor wording appears only in allowed positions.
- No Petraclus or Aiva product cards appear.
- No deleted Carina URLs are linked.
- Sitemap and robots.txt exist.
- Deploy script is documented but does not run automatically.
