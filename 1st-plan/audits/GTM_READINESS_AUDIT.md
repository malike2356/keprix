# Carina Ecosystem - Go-To-Market Readiness Audit

**Date:** 2026-06-30
**Scope:** All products under the Carina/Verlox umbrella
**Purpose:** Honest assessment of where everything stands, what exists, what is missing,
and the critical path to first revenue for each product.

---

## The Single Most Important Truth

The prompt libraries for Keprix and Petraclus are specifications, not code.
They are excellent, comprehensive, implementable specifications. But they do not run.
No subscriber can sign up, no key can be issued, no lab can be started, no report
can be generated until those prompts are given to a developer (or AI) and turned
into actual application code.

Scout is the exception. Scout has 393 TypeScript source files, a working Docker
stack, 6 alert channels, kill switch infrastructure, and a real marketing site.
Scout is the only product in this ecosystem that could be sold tomorrow.

Everything else exists on a spectrum from "research only" to "fully specced with
zero code."

---

## Product Status Matrix

| Product | Code Status | Spec Status | Legal | Marketing Site | Revenue Ready |
| --- | --- | --- | --- | --- | --- |
| Scout | BUILT (393 TS files, Docker, deploy scripts) | Complete | Missing placeholders | EXISTS (labyrinthscout.com) | Near-ready |
| Keys Server | PARTIAL (Python FastAPI, Stripe partial) | BUILD_PROMPT.md exists | None specific | None | Needs completion |
| Carina Aiva | LARGE FRONTEND (20k files), backend unclear | 12 RAG docs, 26 SOPs, 4 pending prompts | 3 docs (placeholders) | EXISTS (carinaai.uk) | Email Handler MVP not built |
| Carina Keprix | ZERO code (core/README.md only) | 51 prompts, complete | 3 docs | None | Not built |
| Petraclus | ZERO code | 49 prompts, complete | 4 docs | None | Not built |
| Petraclus Academy | ZERO code | Prompts 40-49, complete | Partial (no TOS addendum) | None | Not built |
| Fleetz | ZERO code | Market research only | None | None | Concept stage |
| NHS (CompasLab) | ZERO code | Strategy docs | None | None | Concept stage |

---

## Domain-by-Domain Audit

---

### CODEBASE

**Scout** (aiva/02-backends/)
- `scout-engine/`: core event processing, scoring, Redis, DB migrations - EXISTS
- `console.labyrinthscout.com/`: 393 source files including alerts (email, SMS, Slack,
  Discord, Telegram, WhatsApp), compliance, kill switch, API routes, SSE, scheduler - EXISTS
- Marketing site (`03-frontends/marketing/labyrinthscout.com/`): full HTML/CSS/JS site - EXISTS
- Docs site (`03-frontends/marketing/docs.carinaai.uk/`): Docusaurus - EXISTS
- Main Carina AI marketing site (`03-frontends/marketing/carinaai.uk/`): EXISTS

Status: substantially built. Missing: end-to-end integration testing, production
deploy verification, billing connection to keys server.

**Keys Server** (carina/keys-server/)
- `app/main.py`, `billing.py`, `stripe_prices.py` - EXISTS
- `app/api/webhooks.py`, `app/api/scout.py` - EXISTS
- `app/core/scout_provision.py`, `config.py` - EXISTS
- Docker, requirements.txt - EXISTS

Status: partial. Has Stripe webhook handling and Scout provisioning. Missing:
Keprix key provisioning, Petraclus key provisioning, full key generation and
validation endpoints, customer portal, usage tracking.

**Carina Aiva** (carina/aiva/)
- 03-frontends: 20,052 files - a very large frontend codebase EXISTS
- 02-backends: only Scout engine is here (no separate Aiva API server visible)
- The AI employee feature (email handler MVP) - NOT FOUND in code

Status: substantial frontend exists. The AI employee backend either lives inside
the frontend as server-side routes, or it has not been built. The pending prompts
(ICP, pricing, launch readiness, email handler MVP) confirm the AI employee feature
is not yet built.

**Carina Keprix** (carina/keprix/)
- core/README.md - that is the entire codebase
- 51 build prompts - complete specifications
- Pitch materials - video, audio, PDF, image
- Legal docs, README, engineering pillars

Status: ZERO application code. Keprix is the AI backbone for both Petraclus and Aiva.
Until Keprix is built, neither of those products can function.

**Petraclus** (carina/petraclus/)
- prompts/: 49 complete build prompts
- legal/: 4 legal documents
- academy/: 5 non-code guideline documents

Status: ZERO application code. Comprehensive specification only.

---

### TECHNICAL INFRASTRUCTURE

**What exists:**
- Docker Compose files for Scout and keys-server
- Supervisor/systemd deploy scripts for Scout engine
- nginx config for Scout console
- VPS on Contabo (aman) running propreneur.uk

**What is missing:**

For Scout:
- Production deployment verification (is it actually live and stable?)
- Automated backup for Scout PostgreSQL data
- Uptime monitoring (Scout monitors others but who monitors Scout?)
- SSL auto-renewal confirmation

For Keprix (before it can exist):
- VPS provisioning or cloud instance for Keprix
- Docker registry setup (ghcr.io/malike2356/carina-keprix image to build and push)
- Reverse proxy config for Keprix at its eventual domain

For Petraclus Academy (the hardest infra problem):
- Docker-in-Docker or Docker socket access for lab VM orchestration
  (Academy spins student lab containers; the Petraclus container must be able to
  do this - complex security configuration)
- Subnet pool management for per-student network isolation
- Sufficient VPS RAM to run concurrent student labs (each student = 2-4 containers,
  each 512MB-1GB RAM; 20 concurrent students = 40-80 containers = 20-80GB RAM needed)
- Object storage for lab snapshots and evidence vault files
- The lab VM Docker images (10 vulnerable containers from Prompt 41b) need to be
  built and pushed to a registry before any Academy module can run

For the keys server:
- Production domain (keys.carinaai.uk) - DNS and SSL not confirmed
- Database for key storage and activation records

**The infrastructure gap is severe for Academy.** Running 20 concurrent students
in isolated Docker lab environments requires dedicated infrastructure with significant
RAM. A standard £20/month VPS will not support more than 2-3 concurrent students.
Budget for a dedicated instance with 32-64GB RAM before Academy can accept real users.

---

### LEGAL

**What exists:**
- Aiva: Privacy Policy, Data Processing Agreement, Terms of Service
- Keprix: Privacy Policy, Terms of Service, Responsible Disclosure Policy
- Petraclus: Privacy Policy, Terms of Service, Authorized Use Policy, DPA
- Petraclus Academy: LEGAL_REVIEW_GUIDELINES.md (a checklist, not a legal document)

**Universal placeholders (unfilled across all documents):**
- Company registration number - NOT FILLED
- Registered address - NOT FILLED
- Effective dates - NOT FILLED on any document

These documents cannot be published or presented to users until these three fields
are completed. This requires Verlox Limited to be either already registered with
Companies House or to be registered before launch.

**Missing legal documents:**

For Academy (must-have before a single subscriber can enroll):
- Academy Terms of Service addendum (the main Petraclus TOS does not cover lab
  environments, CMA 1990 compliance, age verification mechanics)
- Independent Contractor Agreement for contributors (must be solicitor-drafted, not
  written in-house; see Prompt 49)
- The CMA 1990 enrollment gate text needs solicitor review before going live

For contributors:
- The ICA template (referenced in Prompt 49, not yet written)
- Data processing notice for contributor tax information

For the keys server:
- No legal terms for the key issuance service

For Keprix (open source):
- MIT licence confirmed in README but no LICENCE file in the codebase directory
- Contributor Licence Agreement (CLA) for open source contributions

**ICO registration:**
- Verlox must be registered with the ICO as a data controller if processing UK
  personal data. Academy adds new categories (health/vulnerability indicators from
  student lab behavior could be considered sensitive). ICO registration must be
  updated before Academy launches.

**What requires a solicitor before launch:**
1. ICA template for contributors
2. CMA 1990 enrollment gate text review
3. Academy TOS addendum
4. Confirmation that "worker" classification risk is addressed in ICA (Uber v Aslam)

---

### FINANCIAL

**What exists:**
- Stripe partial integration in keys-server (webhooks, price setup script)
- Business model document for Academy (BUSINESS_MODEL.md)
- Pricing defined across all products (Prompt 49, PRODUCT_POSITIONING.md)

**What is missing:**

**Stripe setup (incomplete):**
- Scout Monitor and Govern products - are they live on Stripe? Needs verification.
- Aiva Starter, Growth, seat products - not created on Stripe
- Keprix Free, Basic, Pro key products - not created on Stripe
- Petraclus Community, Academy, Pro, Team products - not created on Stripe
- Stripe Connect for contributor payouts - not set up
- Customer portal for subscription management - not configured
- Stripe webhook endpoints for all products - partial (Scout only)

**No payment flow currently works for:**
- Aiva subscriptions
- Keprix key purchases
- Petraclus subscriptions
- Academy subscriptions
- Contributor payouts

**Accounting and tax:**
- No accounting system confirmed (Xero, QuickBooks, FreeAgent?)
- VAT registration status unknown - if Verlox earns over £90,000/year (2026
  threshold), VAT registration is mandatory. Below that, optional. If selling
  B2B (Pro/Team users who are VAT registered businesses), VAT-registered status
  is preferable as customers can reclaim it.
- HMRC self-assessment/corporation tax preparation - no process documented
- Contractor payment record-keeping - requirements documented in Prompt 49 but
  no accounting workflow

**Banking:**
- Business bank account assumed to exist for Verlox Limited
- Stripe payouts destination - not documented

---

### SECURITY

**What exists:**
- Scout: kill switch infrastructure, audit logging, Redis-backed controls
- Aiva: SOPs 017 (security hardening) and 018 (security incident SLA)
- Petraclus prompts: security foundation (Prompt 02), audit log (Prompt 07),
  authorized use policy, enrollment gate
- Keys server: no security review documented

**What is missing:**

**For all products before launch:**
- No penetration test of any product has been conducted
- No bug bounty program (this is especially important for Petraclus, a security
  product; launching without a coordinated disclosure policy is a credibility issue)
- Rate limiting: documented in prompts but not verified in running code
- Session management: no audit of existing Scout/Aiva session handling
- Secrets management: .env files and .env.example files suggest environment variables;
  no secrets rotation policy

**For Academy specifically (highest risk):**
- Docker socket security: giving Petraclus the ability to create containers is a
  significant attack surface. If exploited, an attacker could create privileged
  containers and escape the host. Requires careful sandboxing (Docker-in-Docker
  with restricted permissions, or a dedicated orchestration VM separate from the
  main application)
- Student lab isolation: the iptables rules and subnet management from Prompt 41
  need penetration testing before students are trusted to attack them
- CMA 1990 offense risk: if a student uses Academy tools against unauthorized
  systems, Verlox needs clear evidence of the enrollment gate acceptance to
  demonstrate the legal boundary was communicated

**No security testing process exists for any product.**
This is the highest-risk gap. Petraclus is a security product. If it ships with
security vulnerabilities, the damage to reputation is catastrophic and immediate.
Minimum viable security before launch: automated SAST scanning in CI/CD (Snyk,
CodeQL, or equivalent) and at least one manual code review of authentication flows.

---

### MARKETING

**What exists:**
- labyrinthscout.com: full marketing site (HTML, service worker, manifest)
- carinaai.uk: marketing site exists (files present)
- docs.carinaai.uk: Docusaurus documentation site
- Keprix pitch materials: PDF, video, audio, image (in pitch-and-sell/)
- PRODUCT_POSITIONING.md: complete positioning document
- STRATEGY_AND_ASSESSMENT.md: full ecosystem strategy

**What is missing:**

**Marketing sites not built:**
- petraclus.com: NO marketing site exists. Prompt 27 specifies it but zero files.
- carina-keprix landing page: Keprix is open source; its marketing is GitHub README
  plus a site. No site exists. The GitHub repo itself may not be polished.
- Academy page within petraclus.com: does not exist

**No email sequences exist for any product:**
- Welcome email after sign-up
- Trial expiry warning
- Upgrade nudge (Academy to Pro conversion)
- Contributor onboarding sequence
- Monthly payout notification (template only, no email platform configured)

**Email platform:**
- Resend (primary) and Postmark (fallback) are named in legal docs
- No Resend account setup documented
- No email templates built
- No domain authentication (SPF, DKIM, DMARC) confirmed for sending domains

**Content marketing:**
- No blog
- No SEO strategy
- No keyword research
- No content calendar
- No social media accounts documented or active

**Contributor recruitment:**
- The contributor program is designed but there is no outreach plan
- No list of target contributors (specific people with OSCP, CREST CRT, etc.)
- No cold outreach template
- No way for someone to discover the contributor program exists (no landing page)

**Product Hunt, Hacker News, Reddit:**
- No launch plan for any product
- No pre-launch waitlist for Academy or Petraclus
- Open source Keprix launch (GitHub + HN Show HN) not planned

---

### WHAT IS GENUINELY COMPLETE

These things are done and require no further work before use:

1. **Scout application code** - 393 TypeScript source files, build and deploy ready
2. **Petraclus build specification** - 49 prompts, comprehensive, implementable
3. **Keprix build specification** - 51 prompts, comprehensive, implementable
4. **Academy specification** - 10 prompts (40-49), comprehensive, includes business model
5. **Contributor program design** - guidelines, compensation model, legal framework all specced
6. **Product positioning** - PRODUCT_POSITIONING.md complete
7. **Pricing architecture** - all tiers defined and consistent across documents
8. **Legal document drafts** - need placeholders filled and solicitor review, but content is done
9. **RAG documents for Aiva** - 12 RAG docs complete
10. **Aiva SOPs** - 26 operational procedures documented
11. **Business model validation** - BUSINESS_MODEL.md with unit economics and projections

---

## Must-Have Before ANY Product Ships

These are blocking. Nothing goes live without them.

| # | Item | Blocks | Effort |
| --- | --- | --- | --- |
| 1 | Company number and registered address filled in all legal docs | Every product | 1 day (get Companies House number) |
| 2 | Effective dates set on all legal documents | Every product | 1 hour |
| 3 | ICO registration (or confirmation existing registration covers new data) | Every product | 1-3 days |
| 4 | Stripe products created for Scout (if not already live) | Scout revenue | 2 hours |
| 5 | Domain authentication (SPF/DKIM/DMARC) for sending domains | Email deliverability | 2 hours |
| 6 | Resend account configured with templates for at minimum: welcome, payout | Contributor program | 1 day |
| 7 | Solicitor review of ICA template | Contributor payouts | 1-2 weeks (external) |
| 8 | Solicitor review of Academy enrollment gate CMA text | Academy launch | 1-2 weeks (external) |
| 9 | petraclus.com domain registered and pointed | Petraclus launch | 1 day |
| 10 | Academy TOS addendum written | Academy launch | 2 hours |

---

## Must-Have Before Each Product Ships (Code)

### Scout (closest to launch)
- Verify end-to-end subscription flow: customer signs up, Stripe charges, key issued, Scout configured
- Keys server provisioning for Scout keys must work end-to-end
- Automated test run and no critical failures
- Production deploy to VPS with SSL confirmed

### Carina Keprix (next priority after Scout - everything depends on it)
- Implement prompts 00-16 (foundation through API surface): this is the MVP
- Prompts 17-51 are enhancements; do not block on them
- Build and push Docker image to ghcr.io/malike2356/carina-keprix
- Polish GitHub README (this IS the Keprix marketing page)
- Tag v0.1.0 release

### Carina Aiva (AI Employee Email Handler MVP)
- Requires Keprix running as backbone
- Implement email handler: IMAP poll, draft, 4-hour approval window (specced in aiva-launch-readiness.md)
- Connect to keys server for Aiva tier gating
- First customer onboarding tested end-to-end

### Petraclus (after Keprix is built)
- Implement prompts 00-09 (foundation through reporting): MVP
- Tool suite (prompts 10-20) can be phased post-launch
- Marketing site (petraclus.com) must exist before launch

### Petraclus Academy (after Petraclus Core v1.0)
- The 10 Academy prompts form the complete spec
- Lab infrastructure is the hardest build: Docker orchestration, network isolation
- Minimum: 2 complete learning paths (not 10) at launch
- Contributors not needed at launch: ship with 2 internal paths, open contributor
  program at month 3 once quality bar is proven

---

## Nice-to-Have (Post-Launch, Scale Features)

These are real and valuable but do not block first revenue:

- On-chain anchoring for verification reports (Phase 3, post 1,000 reports)
- Multi-language Academy content
- Mobile app for any product (desktop-only is the right call at launch)
- Fleetz (fleet tracking) - concept stage, not yet a priority
- NHS products (CompasLab, FederateLab) - concept stage
- White-label Keprix for enterprises
- Corporate training packages for Academy (bulk enrollment)
- CREST or NCSC accreditation for Academy (post 1,000 completions)
- Keprix mobile native apps (Prompt 18) - post-MVP
- Keprix marketplace/hub (Prompt 44) - post-MVP
- Conference speaking programme for Expert contributors
- Petraclus Team client portal (Prompt 25) - post-MVP

---

## The Critical Path

The single most important build decision: **build Keprix first.**

Keprix is the AI backbone for both Petraclus and Aiva. Without it:
- Petraclus has no AI correlator, no AI instructor, no report writing
- Aiva has no AI employee capability
- Academy has no AI instructor

Every day Keprix is unbuilt is a day Petraclus and Aiva cannot be built.

**Recommended sequence:**

**Month 1-2:** Keprix MVP (prompts 00-16)
- Foundation, key system, security, agent engine, LLM routing, tools, memory, vault
- Ship as open source on GitHub
- Write GitHub README as the marketing page
- Get the Docker image on ghcr.io

**Month 2-3:** Scout to paying customers
- Scout code exists; connect to keys server end-to-end
- Fill legal placeholders, get solicitor to review
- First 10 paying Monitor subscribers as proof of revenue

**Month 3-5:** Petraclus Core (prompts 00-09)
- Foundation, key system, security, Keprix SDK, cases, tools, findings, audit,
  correlator, reports
- Minimal UI (Prompt 21 - enough to be usable)
- 5 beta users from security community

**Month 5-7:** Academy Phase 1 (prompts 40-47)
- 2 complete learning paths, not 10
- Lab infrastructure for up to 20 concurrent students
- Contributor program opens at month 6

**Month 6+:** Aiva Email Handler MVP
- Aiva runs on top of Keprix
- First AI employee feature: email handler with approval flow
- Target: first paying Aiva Starter customer

---

## Is This The Full Comprehensive GTM Code and Prompts?

**Prompts:** Yes, for Keprix, Petraclus, and Academy the specification is comprehensive.
A competent developer can take these prompts and build the full product without asking
many questions. The prompts cover architecture, schema, business logic, security,
testing criteria, and acceptance criteria for every feature.

**Code:** No. The prompts are not code. Scout is the only product with real running
code. Keprix, Petraclus, and the full Academy have zero application code.

**GTM as a whole:** No, not complete. The following are missing and are required
for a complete go-to-market:

1. Keprix application code (must be built first)
2. Petraclus application code (must be built second)
3. Academy application code and lab infrastructure (must be built third)
4. petraclus.com marketing site
5. Keprix GitHub README (the open-source marketing page)
6. Email sequences (at minimum: welcome, payout notification, upgrade nudge)
7. Legal placeholders filled (company number, address, dates)
8. ICO registration confirmed
9. Stripe products created and working for all products
10. At least one solicitor review (ICA, Academy enrollment gate)
11. SAST security scanning in CI/CD before any product goes live
12. Contributor recruitment plan (who are the first 5 contributors?)

What you have is a blueprint that would cost significantly more and take far longer
without it. The specifications are the hardest intellectual work. Building the code
from the specs is the mechanical (though still substantial) work.

The honest GTM completion estimate: Scout is at 85%, Aiva at 40%, Keprix at 15%
(specs done, code at zero), Petraclus at 10% (specs done, code at zero).

---

## Missing Prompts / Specs (Gaps in the Specification)

Even at the specification level, these are not yet written:

| Missing Spec | Product | Priority |
| --- | --- | --- |
| Academy TOS addendum | Petraclus/Academy | Must-have |
| ICA template for contributors | Academy | Must-have (solicitor) |
| Petraclus marketing site spec (what goes on petraclus.com) | Petraclus | Must-have |
| Keprix GitHub README (the open source landing page) | Keprix | Must-have |
| Email template specs (what do onboarding emails say) | All | High |
| Stripe product setup runbook (step-by-step for all products) | All | High |
| Scout production deploy runbook | Scout | High |
| Keys server completion spec (Keprix and Petraclus key endpoints) | Keys | High |
| Petraclus CI/CD pipeline spec | Petraclus | Medium |
| Academy contributor recruitment plan (first 10 contributors) | Academy | Medium |
| Monitoring and alerting spec for Petraclus itself | Petraclus | Medium |
| Disaster recovery plan | All | Medium |
| Support process (how do users get help?) | All | Medium |
| Aiva email handler MVP implementation prompt | Aiva | High |
