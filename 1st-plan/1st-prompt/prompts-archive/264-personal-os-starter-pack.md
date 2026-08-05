# Keprix - Prompt 264: Personal OS Starter Pack

**Series:** Agentic OS adoption **256-265**  
**Master reference:** `../prompts-archive/ref-255-agentic-os-adoption-master-reference.md`  
**Depends on:** **256**, **258**  
**Working directory:** `/opt/lampp/htdocs/verlox/keprix/`

---

## 1. What this prompt builds

Hub-distributable **Personal OS** `.kxpack` seeding:

- Knowledge Pipeline workspace template (**258**)
- Sample skills: `daily-brief`, `inbox-triage`, `research-to-wiki`
- Nate skills (**274-276**): `onboard`, `four-cs-audit`, `level-up`
- Pre-filled **256** audit checklist (domains, example tasks)
- Link to **265** onboarding checklist
- Optional Agent App stubs for daily-brief

**Non-goals:** Chase AI Plus proprietary assets; generic Keprix-branded samples only.

---

## 2. Pack structure

```text
personal-os-starter/
  manifest.json
  skills/
    daily-brief/SKILL.md
    inbox-triage/SKILL.md
    research-to-wiki/SKILL.md
    onboard/SKILL.md              # 276
    four-cs-audit/SKILL.md        # 274
    level-up/SKILL.md              # 275
  workspace-templates/knowledge_pipeline/
  workspace-templates/executive_assistant/   # 278 hot.md seed
  connections.md.tpl               # 277
  agent-apps/daily-brief/agent.yaml
  audit-seed.json              # importable by 256
  README.md
```

Manifest id: `keprix-personal-os-starter`, tier: free, category: productivity.

---

## 3. Install flow

Hub **Install** or:

```bash
keprix packs install personal-os-starter
keprix agent-os audit import --seed personal-os-starter/audit-seed.json
keprix workspace init --template knowledge_pipeline --name personal-os
```

Web: `/hub` card "Personal OS Starter" with post-install wizard (3 steps: workspace, review audit, pin actions on **262**).

---

## 4. Sample skill requirements

Each skill must meet `AGENTS.md` skill standards (description <= 60 chars, tests in `tests/skills/`).

| Skill | Purpose |
| --- | --- |
| `daily-brief` | Calendar + tasks + memory summary |
| `inbox-triage` | Email triage draft (uses existing email tools if configured) |
| `research-to-wiki` | Raw file -> wiki article in vault |
| `onboard` | Seven-question interview -> `context/` (**276**) |
| `four-cs-audit` | Scored OS maturity audit (**274**) |
| `level-up` | Post-audit remediation plan (**275**) |

Skills degrade gracefully when email/calendar not configured (readiness message, not crash).

---

## 5. Files to create

```
src/keprix/packs/catalog/personal-os-starter/   # or hub seed path
  manifest.json
  skills/...
  workspace-templates/...
  agent-apps/daily-brief/...
  audit-seed.json
  README.md

src/keprix/agent_os/audit_seed_importer.py

frontend/src/components/hub/PersonalOsStarterCard.tsx

docs/features/personal-os-starter-pack.md

tests/
  test_personal_os_pack_install.py
  test_audit_seed_importer.py
  skills/test_daily_brief_skill.py
  skills/test_inbox_triage_skill.py
  skills/test_research_to_wiki_skill.py
```

Register pack in Hub catalog API.

---

## 6. Acceptance criteria

- One-click Hub install adds skills to registry and shows in `/hub` installed list.
- Workspace init from pack creates **258** layout with indexes.
- Audit seed imports into **256** store as editable draft audit.
- Post-install wizard completes without stubs; final step deep-links to `/agent-os` with suggested pins.
- Pack passes `keprix packs verify` and skill lint rules.

---

## 7. Dependencies

- **262** suggested pins documented in README
- **264** can ship before **262** if wizard step is "Pin actions (after 262)"
- **274-277** Nate skills and connections template ship with or before pack v1.1
