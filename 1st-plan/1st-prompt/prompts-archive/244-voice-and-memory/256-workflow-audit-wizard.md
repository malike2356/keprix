# Keprix - Prompt 256: Workflow Audit Wizard

**Series:** Agentic OS adoption **256-265** (Chase AI patterns).  
**Master reference:** `../prompts-archive/ref-255-agentic-os-adoption-master-reference.md`  
**Working directory:** `/opt/lampp/htdocs/verlox/keprix/`

---

## 1. What this prompt builds

A **Workflow Audit Wizard**: the productized entry point for Level 1 (skill architecture). Operators codify day/week work into skill candidates before prompt **257** packages them.

Three audit modes (from the Chase video):

| Mode | Operator flow |
| --- | --- |
| **Manual** | Checklist by domain; add tasks; mark skill-worthy |
| **Session scan** | Pick last N sessions; API returns repeated task chart |
| **Interview** | Stream-of-consciousness chat; agent asks blind-spot questions |

Output: `WorkflowAuditResult` with tasks, proposed skills, proposed automations, exported JSON for **257**.

**Non-goals:**

- No auto-create skills (approval stays in **257**)
- No Obsidian-specific UI
- No custom social/vanity metrics

---

## 2. Already built (do not reimplement)

| Area | Location |
| --- | --- |
| Session store | `keprix_state.py` / SessionDB |
| Session search | `session_search` tool, `/api/sessions` |
| Skills registry | `skills/`, `skill_manage` tool |
| Improvement proposals | `improvement/run_analyzer.py`, `improvement/routes.py` |
| NL drafting | `playbook/nl_builder.py` (208) |
| Hub / skills UI | `/hub`, workspace Skills |

---

## 3. Architecture

```text
/agent-os/audit  (wizard UI, 3 tabs)
        |
        v
workflow_audit_service.py
  - manual_audit_store
  - session_scan (delegates preview to 257 extractor stub interface)
  - interview_transcript
        |
        v
POST /api/agent-os/audit/start|continue|complete
        |
        v
WorkflowAuditResult JSON  -->  257 skill proposals (import endpoint)
```

---

## 4. Data model

```python
@dataclass
class AuditTask:
    id: str
    domain: str              # e.g. content, sales, research
    description: str
    frequency: str           # daily | weekly | ad_hoc
    desired_output: str
    tools_hint: list[str]
    propose_skill: bool
    propose_automation: bool

@dataclass
class WorkflowAuditResult:
    audit_id: str
    mode: str                # manual | session_scan | interview
    tasks: list[AuditTask]
    proposed_skills: list[dict]   # slug, name, rationale
    proposed_automations: list[dict]  # type cron|playbook|agent_app, name
    session_ids_scanned: list[str]
    completed_at: str
```

Persist under `{KEPRIX_HOME}/agent-os/audits/{audit_id}.json`.

---

## 5. API routes

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/api/agent-os/audit/start` | `{ mode, domain?, session_count? }` |
| POST | `/api/agent-os/audit/{id}/continue` | Interview turn or manual patch |
| POST | `/api/agent-os/audit/{id}/complete` | Finalize result |
| GET | `/api/agent-os/audit/{id}` | Fetch result |
| GET | `/api/agent-os/audits` | List past audits |
| POST | `/api/agent-os/audit/{id}/export-to-proposals` | Push to **257** proposal queue |

---

## 6. UI (`/agent-os/audit`)

**Tab 1 - Manual:** domain chips (content, sales, ops, research, custom); task table with add row; toggle "Make skill" / "Automate later".

**Tab 2 - Session scan:** slider 5-50 sessions; "Scan" calls backend; table: task, count, tools, proposed skill name.

**Tab 3 - Interview:** textarea + chat panel; agent asks follow-ups; ends with summary table.

**Completion screen:** export to skill proposals, download JSON, link to **258** workspace template if no vault yet.

Sidebar entry: **Agent OS > Workflow audit** (feature flag `agent_os.enabled`, default true on new installs).

---

## 7. CLI

```bash
keprix agent-os audit start --mode session-scan --sessions 10
keprix agent-os audit list
keprix agent-os audit show <audit_id>
keprix agent-os audit export <audit_id> --to-proposals
```

---

## 8. Files to create

```
src/keprix/agent_os/
  __init__.py
  workflow_audit_service.py
  audit_store.py
  interview_agent.py          # thin wrapper over AIAgent with fixed system prompt

src/keprix/api/
  agent_os_audit_routes.py

frontend/src/app/(workspace)/agent-os/
  audit/
    page.tsx
    ManualAuditTab.tsx
    SessionScanTab.tsx
    InterviewTab.tsx
    AuditSummary.tsx

frontend/src/lib/agentOsNav.ts   # sidebar links

docs/features/agent-os-workflow-audit.md

tests/agent_os/
  test_workflow_audit_service.py
  test_audit_store.py
  test_agent_os_audit_routes.py
```

Wire routes in `web_server.py` (or existing API router pattern).

---

## 9. Acceptance criteria

- Operator completes all three modes without stubs; each persists `WorkflowAuditResult`.
- Session scan mode reads real sessions from SessionDB and returns at least task descriptions (clustering can be heuristic v1; no fake data).
- Interview mode runs real agent turns with audit-scoped system prompt.
- "Export to proposals" creates rows consumable by **257** API (contract documented in both prompts).
- CLI commands work against same store as UI.
- Feature flag `agent_os.enabled` hides routes when false.
- Tests cover start/complete/export for manual mode and API auth.

---

## 10. Dependencies

- **Next:** 257 (session-to-skill) imports proposals from this audit.
- **Parallel:** 258 workspace template linked from completion screen.
