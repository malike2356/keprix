# Nate Herk AIOS Adoption Master Reference (Keprix 274-279)

**Source:** [Build & Sell Claude Code Operating Systems](https://www.youtube.com/watch?v=bCljOfCH8Ms)  
**Transcript:** `planning/competitor-research/youtube-bCljOfCH8Ms-transcript.txt`  
**Competitive note:** `planning/competitor-research/nate-herk-aios-adoption.md`  
Prompts 274-279 shipped on 2026-07-09 with 264/265/258 Nate extensions.

---

## 1. Strategic decision (non-negotiable)

| Adopt | Skip |
| --- | --- |
| 4 C's scored OS maturity audit | Claude Code / VS Code as the product |
| Onboard interview skill (7 questions) | Paid Claude subscription requirement |
| `connections.md` tier-1 domain matrix | n8n-era workflow engine pivot |
| AI service account integration pattern | Glido / voice dictation as core feature |
| `hot.md` optional vault cache | Obsidian required for all users |
| Google Workspace connector (GWS-style) | Anthropic Co-work clone |
| 3 M's / 3 habits in onboarding copy | Skill marketplace gold-rush UI |
| Day 1 / 2 / 7 rollout in **265** | Fork Nate's GitHub repo into core |

**Runtime rule:** Nate patterns ship as Keprix skills, vault templates, connectors, and Agent OS extensions. No IDE-specific install flows.

---

## 2. Prompt map

| Prompt | Title | Delivers |
| --- | --- | --- |
| **274** | Four C's OS maturity audit | Scored audit skill + API + `/agent-os/maturity` |
| **275** | Level-up remediation skill | Post-audit fix plan skill paired with **274** |
| **276** | Onboard interview skill | 7-question interview -> `context/` scaffold |
| **277** | Connections tier matrix | `connections.md`, tier-1 domains, service-account docs, day-2 wizard |
| **278** | Hot cache vault layer | Optional `wiki/hot.md` + updater hook |
| **279** | Google Workspace connector | Mail/calendar/drive/sheets tools via GWS-style CLI bridge |

Build order: `273-nate-herk-aios-adoption-build-order.md`

**Amendments (same ship train, no new numbers):**

| Existing | Nate extension |
| --- | --- |
| **258** | `context/` preset files; link **278** hot cache |
| **264** | Pack includes `onboard`, `four-cs-audit`, `level-up` skills |
| **265** | Day 1/2/7 steps; `l0_onboard`, `l2_four_cs_audit` checklist items |

---

## 3. Nate vs Chase vs Keprix

| Layer | Chase (HRw) | Nate (bClj) | Keprix prompts |
| --- | --- | --- | --- |
| Entry audit | Workflow tasks | 4 C's score | **256** + **274** |
| Memory | Workspace map | context/ + wiki | **258**, `llm-wiki`, **278** |
| Skills | Session loop | SOPs + onboard | **257**, **276** |
| Connections | Vault provider | connections.md + GWS | **277**, **279** |
| Cadence | Action board | cron + remote | **260-262** |
| Sell / handoff | Client kit | Build and sell course | **263**, **264** |

---

## 4. Four C's scoring model (274)

| C | Max points | Signals |
| --- | --- | --- |
| Context | 25 | `context/about-*.md`, priorities, writing samples |
| Connections | 25 | Tier-1 domains reachable via **277** matrix |
| Capabilities | 25 | Skills count, automations (**260**), headless (**262**) |
| Cadence | 25 | Cron/playbook schedules, ledger (**261**) |

Output: `MaturityAuditResult` with score, gaps ranked by leverage, export to **275**.

---

## 5. Tier-1 connection domains (277)

| Domain | Examples |
| --- | --- |
| revenue | QuickBooks, Stripe, sheets |
| customer | CRM, support inbox |
| calendar | Google Calendar, Outlook |
| comms | Slack, email, school/community |
| tasks | ClickUp, Asana, Linear |
| meetings | Fireflies, Granola, transcripts folder |
| knowledge | Drive, Notion export, vault wiki |

---

## 6. Verification checklist (pack complete)

| Check | Prompt |
| --- | --- |
| `/four-cs-audit` returns scored report with tier-1 gap list | 274 |
| `/level-up` consumes audit JSON and produces prioritized actions | 275 |
| `/onboard` completes 7 questions; writes `context/*.md` | 276 |
| Day-2 wizard suggests connection priority from **277** | 277, **265** |
| `hot.md` updates after session; agent reads index before wiki crawl | 278 |
| Google mail/calendar list works with configured credentials | 279 |
| **264** pack installs all three Nate skills | 264 amend |
| **265** shows day 1/2/7 + maturity audit step | 265 amend |

---

## 7. Status table

| Area | Status | Prompt |
| --- | --- | --- |
| Workflow task audit | Started (**256**) | 256 |
| 4 C's maturity audit | **Shipped** | 274 |
| Level-up remediation | **Shipped** | 275 |
| Onboard interview | **Shipped** | 276 |
| Connections matrix | **Shipped** | 277 |
| hot.md cache | **Shipped** | 278 |
| llm-wiki | **Shipped** | skill |
| Google Workspace | **Shipped** | 279 |
| Personal OS pack | **Shipped** | 264 |
| Client kit | **Shipped** | 263 |
