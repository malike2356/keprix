# Agentic OS Adoption Master Reference (Keprix 256-265)

**Source:** [Chase AI - The Agentic OS Setup That Will 10x Claude Code](https://www.youtube.com/watch?v=HRw-vP0j8OM)  
**Transcript:** `planning/competitor-research/youtube-HRw-vP0j8OM-transcript.txt`  
**Do not archive until prompts 256-265 ship.**

---

## 1. Strategic decision (non-negotiable)

| Adopt | Skip |
| --- | --- |
| Workflow audit, skills, loop engineering | Jarvis cosplay UI as the product |
| Structured workspace maps (`index.md`, navigation guide) | Rebuilding Obsidian or shipping an Obsidian plugin |
| Headless one-click actions (skills, playbooks, apps) | Chase-specific vanity metrics (YouTube subs, Instagram) |
| Run ledger + eval-backed loop profiles | Second workflow engine (canvas stays in **233-238**) |
| Client kit + simplified mode for distribution | Mandatory Karpathy-only layout (offer as template preset) |

**One runtime rule:** Skills, playbooks, cron, and Agent Apps all execute on the existing Keprix agent core. UI layers trigger headless runs; they do not fork a second agent product.

**Four levels (operator mental model):**

| Level | Chase label | Keprix surface |
| --- | --- | --- |
| L1 | Skill architecture + loop engineering | Prompts **256-257**, **260-261** |
| L2 | Memory + state map | Prompts **258-259** |
| L3 | Visual wrapper + one-click actions | Prompt **262** + KNIME pack **233-238** |
| L4 | Distribution | Prompts **263-265** |

---

## 2. Prompt map

| Prompt | Title | Delivers |
| --- | --- | --- |
| **256** | Workflow audit wizard | Guided audit (manual, session scan, interview) |
| **257** | Session-to-skill automation loop | Pattern detector, proposals, packager, improvement loop |
| **258** | Structured workspace memory | `raw/wiki/outputs` template, auto `index.md`, `KEPRIX.md` |
| **259** | Universal vault provider | Any markdown folder vault; two-way sync |
| **260** | Skill-to-automation promoter | Skill -> cron / playbook / Agent App |
| **261** | Playbook run ledger + loop profiles | Unified run log, baselines, self-improve proposals |
| **262** | Headless action board | Pinned skills, playbooks, apps; headless API |
| **263** | Client kit + simplified mode | Export handoff bundle; hide advanced routes |
| **264** | Personal OS starter pack | Hub `.kxpack` with templates + sample skills |
| **265** | Agentic OS onboarding checklist | In-app 4-level checklist + docs |

Build order: `255-agentic-os-adoption-build-order.md`

---

## 3. Superseded draft files

These unnumbered drafts in `pending-prompts/` are **superseded** by the numbered series (content merged):

| Draft | Replaced by |
| --- | --- |
| `245-structured-workspace-memory.md` | **258** |
| `246-session-to-skill-automation.md` | **257** |
| `247-headless-skill-launcher.md` | **262** |
| `248-universal-vault-provider.md` | **259** |

Do not implement the draft files; use **256-265** only.

**Separate series (do not merge):** Brain graph **246-254** (duplicate numbers in drafts), credentials **239-243**, KNIME **233-238**.

---

## 4. System diagram

```text
                    +---------------------------+
                    | 256 Workflow Audit Wizard |
                    +-------------+-------------+
                                  |
          +-----------------------+-----------------------+
          v                       v                       v
   +-------------+        +-------------+        +-------------+
   | 257 Session |        | 258 Workspace|        | 260 Skill   |
   | to Skill    |        | Memory Map   |        | Promoter    |
   +------+------+        +------+-------+        +------+------+
          |                       |                       |
          v                       v                       v
   +-------------+        +-------------+        +-------------+
   | 261 Run     |        | 259 Vault   |        | cron /      |
   | Ledger      |        | Provider    |        | playbook /  |
   +------+------+        +-------------+        | agent-app   |
          |                                        +------+------+
          v                                               |
   +-------------+        +-----------------------------+
   | 262 Action  |<-------+
   | Board       |
   +------+------+
          |
          v
   +-------------+        +-------------+
   | 263 Client  |        | 264 Starter |
   | Kit         |        | Pack (Hub)  |
   +-------------+        +-------------+
          \___________________/
                    |
                    v
            +---------------+
            | 265 Onboarding|
            | Checklist     |
            +---------------+

Parallel (visual layer): KNIME 233-238, Scout 236
```

---

## 5. Cross-pack dependencies

| Agentic OS prompt | Depends on | Notes |
| --- | --- | --- |
| 257 | 256 (optional entry), `improvement/*` | Uses `run_analyzer.py` |
| 258 | none | Template + indexer |
| 259 | 258 | Vault reads same folder layout |
| 260 | 257 | Promote approved skills |
| 261 | 257, playbooks runtime | Extends improvement to playbooks |
| 262 | 260, 261 | Buttons for all automation types |
| 263 | 262 | Export includes action board config |
| 264 | 256-258 | Pack seeds audit + workspace |
| 265 | all above (stubs OK until shipped) | Checklist marks items done |

**KNIME 233** can ship in parallel with **256-261**. **262** should follow **260** so buttons cover promoted automations.

---

## 6. Verification checklist (pack complete)

| Check | Prompt |
| --- | --- |
| Operator completes workflow audit and gets skill candidates | 256 |
| 3+ session pattern proposes skill; approve creates pack | 257 |
| Knowledge Pipeline workspace has live `index.md` files | 258 |
| External markdown folder works as vault (read + write) | 259 |
| Approved skill promotes to cron or playbook or Agent App | 260 |
| Playbook run writes ledger row; loop profile proposes tweak | 261 |
| Action board runs skill/playbook/app headless | 262 |
| Client kit zip installs on fresh workspace | 263 |
| Hub installs Personal OS pack | 264 |
| Onboarding checklist tracks 4 levels | 265 |

---

## 7. Status table

| Area | Status | Prompt |
| --- | --- | --- |
| Playbook runtime | **Shipped** | 207-211 |
| NL to YAML | **Shipped** | 208 |
| Improvement run analyzer | **Shipped** | improvement/ |
| Visual Playbook Studio | **Shipped** | 233-238 (KNIME) |
| Workflow audit UI | **Shipped** | 256 |
| Session-to-skill loop | **Shipped** | 257 |
| Workspace index map | **Shipped** | 258 |
| Universal vault | **Shipped** | 259 |
| Skill promoter | **Shipped** | 260 |
| Run ledger | **Shipped** | 261 |
| Action board | **Shipped** | 262 |
| Client kit | **Shipped** | 263 |
| Starter pack | **Shipped** | 264 |
| Onboarding checklist | **Shipped** | 265 |

**Pack status:** **Shipped**. Prompts **256-265** are implemented and archived.
