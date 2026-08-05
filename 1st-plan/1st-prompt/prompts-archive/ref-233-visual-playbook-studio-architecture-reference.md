# Keprix - Prompt 233: Visual Playbook Studio Architecture Reference

## Purpose

Reference and dependency map for the **KNIME adoption pack** (prompts **233-238**). Complements prompt **208** (NL to YAML), not replaces it.

**Status:** Keprix KNIME adoption pack shipped through prompt 238.

**Master map:** `233-knime-adoption-master-reference.md`

---

## Problem statement

| Surface | Today | Target |
| --- | --- | --- |
| Authoring | YAML files, Describe tab, Advanced JSON | Drag-and-drop canvas (233) |
| Templates | graph_catalog API only | Studio gallery (237) |
| Variables | Jinja refs in prompts | Declared variables panel (237) |
| Connectors | MCP admin buried | Marketplace (234) |
| Publish | None | Version hash + Scout (236) |
| Import | n8n CLI to YAML | Studio import (238) |
| Run UI | Timeline list | Timeline + canvas overlay (238) |
| Runtime | `yaml_compiler` -> `sdk_workflow` | Unchanged |
| Carina / Aiva | No canvas path | Embed (01) + runner (05) |

Competitive drivers: KNIME, n8n, monday Agent Builder, Box Automate.

---

## Non-goals

- Second workflow engine or KNIME Java port
- Full KNIME connector catalog
- CRDT collaborative editing (defer)
- Replacing Mutation Engine with static node SDK

---

## Architecture (233 core)

```text
/playbooks/studio/[id]  (Next.js + React Flow)
        |
        v
canvas_compiler.py  <->  canvas_decompiler.py
        |
        v
playbook YAML + optional .layout.json
        |
        v
yaml_compiler.compile_playbook_document()
        |
        v
POST /api/playbook-runs/start
        |
        v
PlaybookStepTimeline (+ optional run overlay 238)
```

---

## Node palette (v0 in 233; extended in 237)

| Canvas node | YAML `type` | Prompt |
| --- | --- | --- |
| Trigger | entry metadata | 233 |
| Agent task | `agent_task` | 233 |
| HTTP | `http` | 233 |
| Condition | `condition` | 233 |
| Human approval | `human_approval` | 233 |
| Parallel | `parallel` | 237 |
| Artifact | `artifact` | 237 |

---

## Status table

| Area | Status | Prompt |
| --- | --- | --- |
| Playbook runtime | **Shipped** | 51, 207-211 |
| Run timeline UI | **Shipped** | PlaybookStepTimeline |
| NL to YAML (208) | **Shipped** | nl_builder |
| n8n YAML import (207) | **Shipped** | n8n_converter |
| Visual canvas editor | **Shipped** | 233 |
| Connector marketplace | **Shipped** | 234 |
| Edition gates | **Shipped** | 235 |
| Scout telemetry | **Shipped** | 236 |
| Templates/variables/coach | **Shipped** | 237 |
| Import/run overlay | **Shipped** | 238 |
| Carina embed | **Missing** | knime-adoption--01 |

---

## Build order

See `233-knime-adoption-build-order.md`.
