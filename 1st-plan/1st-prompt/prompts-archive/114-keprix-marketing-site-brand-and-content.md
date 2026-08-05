# keprix - Prompt 114: Standalone Marketing Site Brand And Content

## Purpose

Build the content plan for keprix's own marketing site.

keprix is an independent open-source AI agent operating system. It is not
Carina keprix. It is not powered by Carina. It may say "Sponsored by Carina"
in a quiet footer or sponsor badge only.

This prompt does not build the site implementation. It defines the brand,
information architecture, pages, copy rules, and conversion paths that Prompt 135
must implement.

## Working Directory

Create the marketing source under:

```text
/opt/lampp/htdocs/verlox/keprix/marketing/sites/keprix/
```

If the directory does not exist, create it in Prompt 135.

## Domain

Use a configurable domain in copy and config:

```text
keprix_MARKETING_DOMAIN=keprixai.uk
```

If the final domain changes, the site must be editable through one config file.

## Brand Rules

Allowed:

- Product name: `keprix`
- Short description: `Open-source AI agent OS`
- Sponsor wording: `Sponsored by Carina`
- Optional integration wording: `Works with Labyrinth Scout`
- Repo wording: `GitHub: malike2356/keprix`

Not allowed:

- `Carina keprix`
- `Powered by Carina`
- `Built on Carina`
- `Aiva`
- `Carina Aiva`
- `Petraclus` as part of keprix's product family
- Enterprise upgrade or commercial edition language
- Remote licence keys
- Cybersecurity feature claims that belong to Petraclus

## Audience

Primary:

- Developers building AI products
- Agencies building vertical AI apps
- Self-hosters who want control of data and infrastructure
- Researchers and technical founders
- Teams that want an open AI agent runtime without vendor lock-in

Secondary:

- Universities and students
- Open-source contributors
- Tool and skill-pack authors
- Companies evaluating an AI agent OS before building products on it

## Positioning

Use this positioning:

```text
keprix is the open-source AI agent OS for building AI products.
Ten researched agents, one installable workspace: memory, tools, channels,
model routing, playbooks, durable workflows, and a Mutation engine that builds
new tools after your approval.
```

Tagline (use in hero subheads, metadata, and social cards):

```text
Ten agents. One OS.
```

Extended positioning paragraph:

```text
keprix consolidates the strongest ideas from ten AI agent platforms into a single
MIT-licensed runtime you install on your own hardware. Hermes-grade conversation
and tool loops, Carina-grade workspace and memory, plus orchestration patterns from
LangGraph, CrewAI, and AutoGen, browser automation, analytics workspaces, and
governed self-coding paths. When nothing fits, the Mutation engine proposes a new
tool, sandboxes it, and installs it after you approve.
```

Core promise:

```text
Install the workspace. Connect your models. Let the agent work, remember, and
build new tools after approval.
```

Do not present keprix as a chatbot. Present it as a local AI operating layer.
Do not name upstream projects in user-facing marketing copy. Say what keprix does,
not what it was forked from.

## Homepage Structure

Create a homepage content plan with these sections:

1. Hero
   - H1: `keprix`
   - Subheadline: `Ten agents. One OS. The open-source AI agent platform for building AI products.`
   - Body (one sentence): `One installable workspace with memory, tools, channels, playbooks,
     and a Mutation engine that builds new capabilities after your approval.`
   - Primary CTA: `Get started on GitHub`
   - Secondary CTA: `Read the docs`
   - Tertiary text link: `See what it consolidates`
   - Optional sponsor badge: `Sponsored by Carina`

2. What It Is
   - Explain the AI agent OS analogy clearly.
   - Include kernel, workspace, hub, and playbook language.
   - Avoid Linux trademark overuse. Analogy is fine, dependency is not.

3. Ten Agents, One OS
   - Dedicated section explaining consolidation without naming upstream repos in prose.
   - Use a capability grid, not a competitor comparison table.
   - Rows (capability label only, no upstream names):
     - Agent core and tool loop
     - Multi-channel gateway
     - Research and search workspace
     - Memory and RAG
     - Durable playbooks and workflows
     - Multi-agent teams
     - Browser automation
     - Analytics and code workspace
     - Governed self-coding
     - Optional Scout governance (paid connector)
   - Footer note on the section: `keprix rebuilds these patterns under one brand and one
     approval model. Upstream projects are research references, not runtime dependencies.`

4. Mutation Engine
   - Explain the main differentiator.
   - The agent detects missing capability, proposes a new tool, shows code,
     runs it in a sandbox, waits for approval, then installs it.
   - Include hard approval language. No auto-install without approval.

5. Product Builders
   - Explain how teams can build vertical AI apps on keprix.
   - Examples: borehole drilling assistant, research workspace, estate agency
     assistant, education lab assistant, analytics copilot.
   - Keep examples non-cyber. Cyber belongs to Petraclus.

6. Capabilities
   - Memory and RAG
   - Tool registry
   - Channels
   - Model routing
   - Playbooks and durable workflows
   - Agent teams
   - Browser automation
   - Analytics workspace
   - Slash commands
   - Self-configuration
   - Localisation and voice
   - App Foundation SDK

7. Architecture
   - Local runtime
   - Backend API
   - Web UI, CLI, TUI, mobile companion
   - Skills and packs
   - Optional Scout connector (paid; works without it)
   - No remote licence server

8. Scout Governance (optional)
   - Short section: teams that need kill switches, tamper-evident audit trails, and
     operator-defined policies can connect Labyrinth Scout at full price.
   - Link to `labyrinthscout.com` for pricing and product detail.
   - Do not imply keprix is incomplete without Scout.

9. Community
   - Contribution guide
   - Good first issues
   - Skill-pack contribution
   - Code of Conduct
   - Security reporting

10. Final CTA
   - GitHub
   - Docs
   - Community

## Required Pages

Prompt 135 must implement these pages:

```text
/
/docs/
/docs/quickstart/
/architecture/
/consolidation/
/mutation-engine/
/playbooks/
/hub/
/community/
/contributing/
/security/
/roadmap/
/brand-boundary/
/legal/
```

### `/consolidation/` page

Dedicated page title: `Ten agents. One OS.`

Content rules:

- Explain consolidation in keprix voice. No upstream project names in body copy.
- Capability grid matching section 3 above.
- One paragraph on the Mutation engine as keprix-only.
- One paragraph on optional Scout (paid connector, not bundled).
- CTA back to quickstart and GitHub.

## Copy Requirements

All copy must follow these rules:

- No emojis.
- No em dashes.
- No en dashes.
- Plain ASCII punctuation.
- Direct but warm.
- No "AI magic" language.
- No "autonomous money printer" language.
- No offensive cybersecurity examples.
- No claims that it is production complete unless the feature exists.
- Every risky capability must mention approval gates.
- Every data-handling claim must mention local control or user-managed storage.

## Trust And Safety Copy

Include a trust section:

- Local-first by default.
- Secrets stay in the vault.
- Risky tools require approval.
- Generated tools run in a sandbox first.
- Scout is optional for teams that need external governance.
- keprix works without Scout.

Do not imply users are unsafe without Scout.

## Visual Direction

keprix should feel technical, clean, open-source, and serious.

Use:

- Monospace accents
- Terminal and workspace visuals
- Architecture diagrams
- Code blocks
- Subtle grid or dot surfaces
- Dark and light mode
- High contrast text
- Compact technical sections

Avoid:

- Purple-heavy gradients
- SaaS hero fluff
- Decorative orb backgrounds
- Mascots
- Stock photos
- Overly corporate enterprise copy

## SEO Requirements

Target phrases:

- open-source AI agent OS
- ten agents one OS
- self-hosted AI agent platform
- AI agent workspace
- AI agent tools and memory
- build AI products with agents
- local AI agent runtime
- AI playbook engine
- AI agent consolidation
- mutation engine AI tools

Add metadata for:

- title
- description
- Open Graph
- Twitter card
- canonical URL
- JSON-LD SoftwareApplication

## Acceptance Criteria

- Site copy never says `Carina keprix`.
- Site copy never says `Powered by Carina`.
- keprix is presented as standalone.
- Carina appears only as optional sponsor wording.
- Petraclus appears only as a separate product link, if at all, and never as part
  of the keprix product family.
- Aiva does not appear.
- No cyber tooling is marketed as a keprix feature.
- `/consolidation/` page exists with capability grid and no upstream repo names.
- Hero uses `Ten agents. One OS.` tagline.
- Content is ready for Prompt 135 implementation.
