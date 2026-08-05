# Keprix Prompt 182: Agent Apps - Marketplace Catalog and Sellable Templates

## Purpose

Ship a **curated in-product marketplace**: browse templates, one-click install, categories,
search. Include **3 sellable starter apps** (not hello-world) that demonstrate real value on
first run.

Read reference **177**. Requires **181** (install lifecycle) and **180** (agent runtime for
LLM templates).

---

## Dependencies

- `src/keprix/agent_apps/catalog/` (stubs from **180**)
- Registry install with `source: template`
- Hub Discover tab from **178**

---

## What to build

### 1. Catalog index

```text
src/keprix/agent_apps/catalog/index.json
```

```json
{
  "templates": [
    {
      "id": "daily-standup",
      "name": "daily-standup",
      "display_name": "Daily Standup",
      "description": "Summarises open tasks and recent activity into standup bullets.",
      "category": "productivity",
      "tier": "free",
      "icon": "standup",
      "featured": true
    },
    {
      "id": "research-brief",
      "name": "research-brief",
      "display_name": "Research Brief",
      "description": "Turns a topic into a structured literature-style brief with citations placeholder.",
      "category": "research",
      "tier": "pro",
      "featured": true
    },
    {
      "id": "invoice-review",
      "name": "invoice-review",
      "display_name": "Invoice Review",
      "description": "Extracts line items and flags anomalies from invoice text or PDF paste.",
      "category": "finance",
      "tier": "pro"
    }
  ]
}
```

### 2. Template packages (full apps)

Each folder under `catalog/{id}/`:

```text
agent.yaml          # runtime: agent, inputs, outputs
instructions.md
tools/              # at least one tool yaml
evals/basic.yaml
README.md           # operator-facing what it does
```

**Daily standup**: input `focus` (textarea); uses tasks tool if available; markdown output.

**Research brief**: input `topic`; uses web/research tools; markdown with sections.

**Invoice review**: input `invoice_text` (textarea) or file input; structured json + summary.

All must pass eval suite smoke (mock LLM in CI).

### 3. Catalog API

```python
GET  /api/agent-apps/catalog              # list templates (filter category, q)
GET  /api/agent-apps/catalog/{id}         # detail + readme excerpt
POST /api/agent-apps/catalog/{id}/install # copy to registry, source=template
```

Install returns `{ app, redirect: "/agent-apps/{name}" }`.

### 4. Frontend Discover tab

Replace stub cards in `AgentAppHub`:

- Search box, category chips (productivity, research, finance)
- Template cards: tier badge (Free / Pro), **Install** button
- Installing shows progress; on success navigate to detail
- If already installed: **Open** instead of Install
- Pro templates: show upgrade CTA when billing gate fails (**184** can stub 402 handler)

### 5. Featured row on hub

"Recommended for you" horizontal scroll at top of `/agent-apps` when user has 0-2 installed apps.

### 6. Domain-pack hook (light)

If `domain-packs/{pack}/agent-apps/index.json` exists, merge into catalog response with
`source: domain_pack`. Document in README only; no full domain-pack UI required.

---

## Acceptance criteria

- [ ] Discover tab lists 3 templates from API.
- [ ] One-click install works without CLI.
- [ ] Each template runs end-to-end with configured LLM (manual brief).
- [ ] `tier: pro` template returns 402 or upgrade message when feature off (wire fully in **184**).
- [ ] Tests: catalog list, install copies files, eval smoke per template.

---

## Out of scope

- Third-party hub submission / payments
- Agent studio export as template (**186** mentions only)

---

## Archive

On completion: move to `prompts-archive/`.
