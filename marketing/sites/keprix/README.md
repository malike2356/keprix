# keprix marketing site

Static marketing site for keprix. Deployed to keprixai.uk.

## Stack

Plain HTML, CSS, and vanilla JavaScript. No build step. No framework. No npm. Serve it directly with any web server.

## Directory structure

```
marketing/sites/keprix/
  index.html                  Homepage
  architecture/index.html     System architecture
  consolidation/index.html    Ten agents. One OS. - capability breakdown
  mutation-engine/index.html  Mutation engine detail
  playbooks/index.html        Playbooks and durable workflows
  hub/index.html              Hub session and routing layer
  community/index.html        Community channels and guidelines
  contributing/index.html     Development setup and contribution process
  security/index.html         Security policy and vulnerability reporting
  roadmap/index.html          Public roadmap: Phase 0 through public release
  brand-boundary/index.html   keprix / Carina / Petraclus relationship rules
  legal/index.html            MIT license text and attribution notices
  robots.txt
  sitemap.xml
  assets/
    css/site.css              All styles - CSS variables, components, responsive
    js/site.js                FAQ accordion, sticky header, mobile nav toggle
  scripts/
    deploy.sh                 rsync deploy over SSH
    validate-site.sh          Pre-deploy validation: forbidden strings, required pages
  site.config.json            Site-level configuration values
  REDIRECTS.md                Redirect rules for Nginx / Caddy
```

## Local development

```bash
cd marketing/sites/keprix
python3 -m http.server 8080
# open http://localhost:8080
```

Or with PHP (LAMPP):
```bash
# Site is already served at http://localhost/verlox/keprix/marketing/sites/keprix/
```

## Validation

Run before every deploy:

```bash
./scripts/validate-site.sh
```

This checks for brand boundary violations (forbidden strings), missing required pages, typography rule violations (em dashes, en dashes), and emoji characters.

## Deploy

```bash
export KEPRIX_DEPLOY_HOST="user@203.0.113.10"
export KEPRIX_DEPLOY_PATH="/var/www/keprixai.uk"
./scripts/deploy.sh
```

The deploy script calls validate-site.sh automatically before rsync.

## Content rules

- No em dashes (U+2014). Use a comma, semicolon, or sentence break.
- No en dashes (U+2013). Use a hyphen.
- No emojis anywhere.
- Never: "Carina keprix", "Powered by Carina", "A Carina product", "Aiva".
- Allowed: "Sponsored by Carina" in the footer only.
- No upstream agent names (Hermes, Odysseus, CrewAI, etc.) as keprix feature names.
  They may appear only on /consolidation/ as research attribution.

See /brand-boundary/ for the full brand boundary policy.

## Analytics

No analytics at launch. Site config has `"analyticsProvider": "none"`. To add Plausible:
- Set `"analyticsProvider": "plausible"` in site.config.json
- Add the Plausible script tag to all HTML pages before `</body>`
- Use `"analyticsDomain": "keprixai.uk"` as the data domain

## Licence

MIT. See /legal/ or the repository root LICENSE file.
