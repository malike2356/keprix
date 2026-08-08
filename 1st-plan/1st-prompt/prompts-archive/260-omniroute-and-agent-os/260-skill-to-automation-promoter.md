# Keprix - Prompt 260: Skill-to-Automation Promoter

**Series:** Agentic OS adoption **256-265**  
**Master reference:** `../prompts-archive/ref-255-agentic-os-adoption-master-reference.md`  
**Depends on:** **257** (approved skills)  
**Working directory:** `/opt/lampp/htdocs/verlox/keprix/`

---

## 1. What this prompt builds

One-click **promotion ladder** from codified skill to scheduled automation (Chase: skill -> routine -> loop).

From an approved skill, operator chooses:

| Target | Creates |
| --- | --- |
| **Cron job** | `keprix cron` entry running skill via headless runner |
| **Playbook** | Single-step or multi-step YAML with `agent_task` referencing skill |
| **Agent App** | `agent.yaml` manifest with skill-backed runner |

UI entry points: skill detail, **257** proposal success screen, `/agent-os/promote`.

**Non-goals:** Auto-promote without confirmation; no second scheduler.

---

## 2. Already built

| Area | Location |
| --- | --- |
| Cron | `cron/jobs.py`, `cronjob` tool |
| Playbooks | `playbook/`, NL draft 208 |
| Agent Apps | `agent_apps/`, catalog |
| Skill execution | `agent/skill_commands.py` |

---

## 3. Promoter flow

```text
POST /api/agent-os/promote
  { skill_slug, target: cron|playbook|agent_app, schedule?, name?, deliver_to? }
        |
        v
automation_promoter.py
  - validate skill exists
  - generate artifact (job spec / yaml / agent.yaml)
  - persist link skill_slug <-> automation_id
        |
        v
Return { automation_type, id, edit_url }
```

Store links in `{KEPRIX_HOME}/agent-os/automation-links.json`.

---

## 4. Generated artifacts

**Cron example:**

```json
{
  "name": "daily-brief",
  "schedule": "0 8 * * 1-5",
  "prompt": "/daily-brief",
  "skills": ["daily-brief"],
  "deliver_to": "notification"
}
```

**Playbook example:** one `agent_task` step with tools from skill manifest.

**Agent App example:** minimal `agent.yaml` with `runner: skill`, `skill: daily-brief`, inputs from skill frontmatter if declared.

---

## 5. UI

`/agent-os/promote?skill=daily-brief`

- Step 1: pick target type
- Step 2: schedule (cron/apps) or playbook name
- Step 3: delivery channel for cron
- Step 4: review + create

Show linked automations on skill cards ("Runs as cron: weekdays 8am").

---

## 6. CLI

```bash
keprix agent-os promote --skill daily-brief --to cron --schedule "0 8 * * 1-5"
keprix agent-os promote --skill research-brief --to agent-app
keprix agent-os links --skill daily-brief
```

---

## 7. Files to create

```
src/keprix/agent_os/
  automation_promoter.py
  automation_link_store.py
  templates/cron_from_skill.py
  templates/playbook_from_skill.py
  templates/agent_app_from_skill.py

src/keprix/api/agent_os_promote_routes.py

frontend/src/app/(workspace)/agent-os/promote/page.tsx

docs/features/agent-os-promote.md

tests/agent_os/
  test_automation_promoter.py
  test_automation_link_store.py
```

---

## 8. Acceptance criteria

- Promote skill to cron creates real job visible in `keprix cron list` and runs on schedule (test with short interval in tests).
- Promote to playbook creates valid YAML passing `yaml_compiler.compile_playbook_document`.
- Promote to Agent App creates installable folder under `agent_apps` user space.
- Link store roundtrips; UI shows linked automations on skill hub.
- Uninstalling automation removes link but not skill.

---

## 9. Dependencies

- **262** action board lists promoted automations
- **261** playbook promotions write to run ledger
