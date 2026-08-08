# Keprix - Prompt 260: UI Navigation Architecture

## Purpose of this document

This is the reference architecture for every user-facing screen in keprix. Every
feature prompt written after this one must map its UI to a slot defined here. If a
prompt introduces a new top-level section, it must update this document first.

No feature is complete until it has:
1. A named entry point in this architecture
2. An empty state defined
3. A discovery trigger (how a first-time user finds it without being told)

## Product surface context

Keprix is an agent OS. Three products currently run on it: Aiva, ABBIS, Petraclus.
The navigation architecture applies to all surfaces. Product surfaces (Aiva, ABBIS)
show the same nav structure scoped to their product namespace. The admin layer is
operator-only and never shown to end users of a product surface.

```
Surface resolution:
  keprix native       -> full nav + admin layer visible to workspace owner
  aiva surface        -> full nav scoped to aiva product, no admin layer
  abbis surface       -> full nav scoped to abbis product, no admin layer
  petraclus surface   -> full nav scoped to petraclus product, no admin layer
```

## Navigation structure

```
keprix
├── Home                          /
├── Sessions                      /sessions
│   └── Session detail            /sessions/[id]
├── Brain                         /brain
│   ├── Graph                     /brain/graph
│   ├── Health                    /brain/health
│   ├── Replay                    /brain/replay/[sessionId]
│   └── Shared view (public)      /brain/share/[shareId]
├── Skills                        /skills
│   └── Skill detail              /skills/[id]
├── Tasks                         /tasks
│   ├── Task detail               /tasks/[id]
│   └── Playbook builder          /tasks/playbooks/[id]
├── Tools                         /tools
│   └── Tool detail               /tools/[id]
├── Voice                         /voice
│   └── Call log                  /voice/calls
├── Settings                      /settings
│   ├── General                   /settings/general
│   ├── Voice                     /settings/voice
│   ├── Channels                  /settings/channels
│   ├── API Keys                  /settings/api-keys
│   └── Billing                   /settings/billing
└── Admin (operator only)         /admin
    ├── Products                  /admin/products
    │   └── Product detail        /admin/products/[id]
    ├── Tool ACL                  /admin/tool-acl
    ├── Network Egress            /admin/network-egress
    ├── Quotas                    /admin/quotas
    └── Isolation Audit           /admin/isolation-audit
```

## Primary navigation component

The primary nav is a persistent left sidebar (240px) on desktop, a bottom tab bar
on mobile. It is always visible. It collapses to icons-only at 64px when the user
minimises it.

```
┌────────────────────────┐
│  [K] keprix            │  <- product wordmark / logo
├────────────────────────┤
│  [=] Home              │
│  [#] Sessions          │
│  [o] Brain             │
│  [>] Skills            │
│  [■] Tasks             │
│  [+] Tools             │
│  [~] Voice             │
├────────────────────────┤
│  [*] Settings          │
│  [!] Admin             │  <- only shown to operators
├────────────────────────┤
│  [avatar] User name    │  <- bottom: user menu
│  [%] Quota usage bar   │  <- only shown when quota > 70%
└────────────────────────┘
```

The quota usage bar at the bottom of the sidebar is the primary mechanism for surfacing
resource exhaustion before it becomes a problem. It appears only when the current
product's LLM token usage exceeds 70% of its monthly limit. Clicking it opens
`/settings/billing` or `/admin/quotas` depending on role.

## Section specifications

---

### Home  `/`

**Purpose:** Entry point and orientation. Shows what is happening, what has happened,
and what to do next. Not a dashboard of metrics -- a starting point for action.

**Layout:**

```
┌─────────────────────────────────────────────────┐
│  Good morning, [name].                           │
│  Your agent is ready.           [Start session]  │
├───────────────────────┬─────────────────────────┤
│  Recent sessions      │  Brain                  │
│  ─────────────────── │  342 memories            │
│  Session with Aiva    │  12 skills               │
│  2 hours ago          │  Last updated: now       │
│                       │  [Open brain graph ->]   │
│  Session with Aiva    │                         │
│  Yesterday            ├─────────────────────────┤
│                       │  Active tasks           │
│  [See all sessions]   │  3 running               │
│                       │  [See tasks ->]          │
├───────────────────────┴─────────────────────────┤
│  Discovery card (contextual, see below)          │
└─────────────────────────────────────────────────┘
```

**Empty state (new workspace, zero sessions):**

```
┌─────────────────────────────────────────────────┐
│  Welcome to keprix.                              │
│                                                  │
│  Your AI agent is set up and ready. Start a      │
│  conversation to see what it can do.             │
│                                                  │
│  [Start your first session]                      │
│                                                  │
│  Not sure what to ask?                           │
│  "Help me draft a reply to a client email"       │
│  "Set a reminder to follow up with James"        │
│  "Summarise the documents I uploaded last week"  │
└─────────────────────────────────────────────────┘
```

**Discovery card (progressive, appears below the grid):**

The discovery card rotates through contextual prompts. It appears only when the
condition is true and the user has not dismissed it. One card at a time.

| Condition | Card text | Action |
|-----------|-----------|--------|
| memories >= 10, brain never opened | "Your agent has remembered 10 things. See them as a graph." | Open /brain/graph |
| sessions >= 5, skills count = 0 | "Your agent hasn't learned any reusable skills yet. Add one." | Open /skills |
| tasks exist, playbooks never opened | "You have completed tasks. Turn them into repeatable playbooks." | Open /tasks/playbooks |
| voice not provisioned, 30+ days active | "Give your agent a phone number so clients can call it directly." | Open /voice |
| quota > 80% | "You are using 82% of your monthly token budget." | Open /settings/billing |
| brain health score < 60 | "Your brain has 24 orphaned nodes. Clean them up." | Open /brain/health |

Each card has a dismiss button. Dismissed cards do not reappear for 30 days.

**Feature prompt references:** Home page shell (new prompt required: 261)

---

### Sessions  `/sessions`

**Purpose:** The primary work surface. Where the user talks to the agent. All other
sections exist to support and enhance what happens in sessions.

**Layout (list view):**

```
┌─────────────────────────────────────────────────┐
│  Sessions                      [+ New session]   │
│  [Search sessions...]                            │
├──────────────────────────────────────────────────┤
│  Today                                           │
│  ┌────────────────────────────────────────────┐ │
│  │  Drafted invoice for Kofi Mensah           │ │
│  │  2 hours ago  •  4 messages  •  2 memories │ │
│  │  [Resume ->]              [View in brain]  │ │
│  └────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────┐ │
│  │  Research: Ghana borehole regulations      │ │
│  │  5 hours ago  •  12 messages  •  5 skills  │ │
│  └────────────────────────────────────────────┘ │
│  Yesterday                                       │
│  ...                                             │
└─────────────────────────────────────────────────┘
```

**Session card actions:**
- "Resume" -- open session detail, scroll to bottom
- "View in brain" -- open `/brain/graph` with this session's nodes highlighted
- "Replay" -- open `/brain/replay/[sessionId]` (Prompt 253)

**Session detail `/sessions/[id]`:**

Standard conversation view. Below the last message, a context strip shows what the
agent remembered and which skills it used in this session:

```
  ─────────────────────────────────────────────
  This session  •  3 memories created  •  1 skill used
  [mem: Kofi prefers PDF invoices] [skill: draft_invoice]
  ─────────────────────────────────────────────
```

Clicking a memory or skill opens its node in the brain content panel (Prompt 248)
as a slide-in from the right without leaving the session.

**Empty state (no sessions):** Shown as the home empty state (redirect if sessions = 0).

**Feature prompt references:** Prompts 246-254 (brain entry points), 253 (replay)

---

### Brain  `/brain`

**Purpose:** The agent's memory, made visible. Every memory, skill, task, document,
and session is a node. The brain section makes the agent's knowledge explorable and
manageable.

**Entry points from other sections:**
- Home: "Open brain graph" card
- Sessions: "View in brain" on session cards and context strip
- Discovery card on home when memories >= 10

**Sub-navigation (horizontal tabs under the section header):**

```
Brain  |  Graph  |  Health  |  Replay  |  Export
```

---

#### Brain > Graph  `/brain/graph`

The primary brain view. React Flow canvas (Prompt 247).

**Empty state (zero memories):**

```
┌──────────────────────────────────────────────┐
│                                              │
│         Your brain is empty.                 │
│                                              │
│  Start a session and keprix will remember    │
│  what matters. Memories, skills, and tasks   │
│  will appear here as connected nodes.        │
│                                              │
│  [Start a session]                           │
│                                              │
└──────────────────────────────────────────────┘
```

**First node state (1-9 memories, sparse graph):**

Show the graph normally but include an inline tip card pinned above the filter bar:

```
  Your agent has remembered [N] things so far.
  The graph fills in as you have more conversations.
  [Dismiss]
```

**Populated state:** Full React Flow canvas with:
- Filter bar (Prompt 249) above the canvas
- MiniMap bottom-right (Prompt 247)
- Toolbar top-right: layout selector, zoom controls, Export menu (Prompt 254)
- Node click: slides in content panel from the right (Prompt 248)
- Live activation overlay during active sessions (Prompt 250)

---

#### Brain > Health  `/brain/health`

Brain health dashboard (Prompt 252). Score 0-100, orphan/stale/duplicate detection,
bulk cleanup actions.

**Entry points:**
- Brain sub-nav tab
- Home discovery card when health score < 60
- Brain graph toolbar: "Health" button

**Empty state:** Not applicable -- health runs even on an empty brain (score = 100).

---

#### Brain > Replay  `/brain/replay/[sessionId]`

Session replay on the brain graph (Prompt 253). Accessed from a specific session,
not browseable in isolation.

**Entry points:**
- Session card: "Replay" button
- Session detail context strip: "Replay this session"
- Brain graph: select a session node, "Replay session" in content panel

**Empty state:** If navigated to directly without a valid sessionId, redirect to
`/brain/graph` with a toast: "Select a session to replay."

---

### Skills  `/skills`

**Purpose:** Reusable capabilities the agent has learned or been given. A skill is
a named, repeatable behaviour the agent can invoke without re-explaining it each time.

**Layout:**

```
┌─────────────────────────────────────────────┐
│  Skills                      [+ Add skill]   │
│  [Search skills...]  [Filter: all / active]  │
├─────────────────────────────────────────────┤
│  draft_invoice                               │
│  Drafts a client invoice from a brief.       │
│  Used 12 times  •  Last used: 2 days ago    │
│  [Edit]  [Test]  [Disable]                  │
│                                             │
│  summarise_document                          │
│  Reads and summarises any uploaded document. │
│  Used 3 times  •  Last used: 1 week ago    │
└─────────────────────────────────────────────┘
```

**Skill detail `/skills/[id]`:**
- Skill name, description, prompt template
- Usage history (which sessions invoked it)
- Edit in-place
- "Test this skill" inline chat panel
- Delete (with confirmation)

**Empty state:**

```
┌──────────────────────────────────────────────┐
│                                              │
│  No skills yet.                              │
│                                              │
│  Skills are behaviours your agent learns     │
│  and reuses. You can add one manually or     │
│  ask your agent to learn from a session.     │
│                                              │
│  [Add a skill]                               │
│  [Ask the agent: "Learn from our last chat"] │
│                                              │
└──────────────────────────────────────────────┘
```

**Entry points:**
- Left nav
- Session context strip (skill node clicks)
- Brain graph (skill nodes in content panel have "Edit skill" button)
- Home discovery card when sessions >= 5 and skills = 0

---

### Tasks  `/tasks`

**Purpose:** Autonomous multi-step work the agent does without the user being present
for every step. A task runs in the background and reports back.

**Layout:**

```
┌──────────────────────────────────────────────────┐
│  Tasks                           [+ New task]     │
│  [All]  [Running]  [Completed]  [Failed]          │
├──────────────────────────────────────────────────┤
│  Running                                          │
│  ┌──────────────────────────────────────────────┐│
│  │  Research: Ghana borehole market size        ││
│  │  Started 4 mins ago  •  Step 3 of 7          ││
│  │  [Watch live ->]                             ││
│  └──────────────────────────────────────────────┘│
│  Completed                                        │
│  ┌──────────────────────────────────────────────┐│
│  │  Draft Q2 report                             ││
│  │  Completed 1 hour ago  •  12 steps           ││
│  │  [View output]  [Turn into playbook]         ││
│  └──────────────────────────────────────────────┘│
└──────────────────────────────────────────────────┘
```

**Task detail `/tasks/[id]`:**
- Step-by-step execution trace
- Tool calls made (each expandable: input, output, duration)
- Final output
- "Turn into playbook" button (opens playbook builder)
- "Retry from step N" button for failed tasks

**Playbook builder `/tasks/playbooks/[id]`:**

Visual editor for reusable task sequences (React Flow-based, separate from brain graph).
A playbook is a saved task template with configurable inputs.

**Empty state:**

```
┌──────────────────────────────────────────────┐
│                                              │
│  No tasks yet.                               │
│                                              │
│  Tasks are things your agent does on its     │
│  own, step by step. Give it a goal and       │
│  it works through it while you do other      │
│  things.                                     │
│                                              │
│  Try: "Research the top 5 borehole drilling  │
│  contractors in Accra and summarise them"    │
│                                              │
└──────────────────────────────────────────────┘
```

**Entry points:**
- Left nav
- Home: "Active tasks" widget
- Session: when a session spawns a task, a task pill appears below the message
- Home discovery card when tasks exist but playbooks = 0

---

### Tools  `/tools`

**Purpose:** The integrations that give the agent its reach. Tools connect the agent
to external systems: email, calendar, CRM, search, document stores.

**Layout:**

```
┌───────────────────────────────────────────────────┐
│  Tools                                            │
│  Connected (4)          Available (23)            │
├───────────────────────────────────────────────────┤
│  Connected                                        │
│  ┌──────────────┐  ┌──────────────┐              │
│  │  Gmail       │  │  Google Cal. │              │
│  │  Connected   │  │  Connected   │              │
│  │  [Manage]    │  │  [Manage]    │              │
│  └──────────────┘  └──────────────┘              │
│                                                   │
│  Available to connect                             │
│  ┌──────────────┐  ┌──────────────┐              │
│  │  Stripe      │  │  Notion      │              │
│  │  Payments    │  │  Docs        │              │
│  │  [Connect]   │  │  [Connect]   │              │
│  └──────────────┘  └──────────────┘              │
└───────────────────────────────────────────────────┘
```

**Tool detail `/tools/[id]`:**
- Connection status and credential health
- Permissions granted
- Usage stats (calls this month)
- Disconnect

**Empty state:**

```
┌──────────────────────────────────────────────┐
│                                              │
│  No tools connected.                         │
│                                              │
│  Tools give your agent the ability to read   │
│  your email, manage your calendar, look up   │
│  contacts, and more.                         │
│                                              │
│  [Browse tools]                              │
│                                              │
└──────────────────────────────────────────────┘
```

**Note on Tool ACL (Prompt 256):** Tool ACL is an operator concern, not a user concern.
Regular users see only the tools that their product's ACL permits. They never see a
"blocked by ACL" message on the tools page -- blocked tools simply do not appear in
the available list. The ACL management UI lives exclusively in `/admin/tool-acl`.

---

### Voice  `/voice`

**Purpose:** The agent's phone presence. Provision a phone number, view call history,
configure the receptionist persona.

**Entry points:**
- Left nav
- Settings > Voice
- Home discovery card after 30+ days with no phone provisioned

**Layout (not provisioned):**

```
┌──────────────────────────────────────────────────┐
│  Voice                                            │
│                                                   │
│  Give your agent a phone number.                  │
│                                                   │
│  Clients can call your agent directly. It         │
│  answers, books appointments, takes messages,     │
│  and tells you what happened.                     │
│                                                   │
│  [Set up a phone number]                          │
│                                                   │
│  Powered by Twilio. UK (+44) and Ghana (+233)     │
│  numbers available. ~$0.03/min.                   │
└──────────────────────────────────────────────────┘
```

**Layout (provisioned):**

```
┌──────────────────────────────────────────────────┐
│  Voice              +44 20 1234 5678  [Change]    │
│  Status: Active  •  Persona: Aiva receptionist    │
│  [Edit persona]                                   │
├──────────────────────────────────────────────────┤
│  Recent calls                                     │
│  +44 7700 900123  •  3m 12s  •  Today 14:02       │
│  Booked appointment for James, 3pm Thursday.      │
│  [View session ->]                                │
│                                                   │
│  +233 24 000 1234  •  1m 45s  •  Yesterday        │
│  Caller asked about pricing. Sent follow-up.      │
│  [View session ->]                                │
└──────────────────────────────────────────────────┘
```

Each call creates a keprix session. "View session ->" opens `/sessions/[id]`.

**Feature prompt references:** Prompt 245 (Twilio inbound phone)

---

### Settings  `/settings`

Standard settings shell. Sub-sections:

**General:** Workspace name, timezone, display name, language.

**Voice `/settings/voice`:**
- Phone number provisioning (same UI as `/voice` for users who navigate via settings)
- Receptionist persona editor
- Call forwarding rules

**Channels `/settings/channels`:**
- Email channel (inbound email to agent)
- Slack integration
- WhatsApp (future slot)

**API Keys `/settings/api-keys`:**
- Generate/revoke API keys for programmatic access

**Billing `/settings/billing`:**
- Current plan, usage summary
- Upgrade/downgrade
- Invoice history
- If quotas (Prompt 258) are active, show per-resource usage bars here

---

### Admin  `/admin`

Operator-only. Never shown in the left nav for product surface users (Aiva, ABBIS).
For keprix native users with operator role, shown below a divider in the left nav.

---

#### Admin > Products  `/admin/products`

List of products registered on this keprix instance (Aiva, ABBIS, Petraclus).
Each product card links to its detail page where the operator can:
- View the product's `keprix.yaml` configuration inline
- See current tool ACL summary
- See egress policy summary
- See quota usage summary
- Edit allowed_tools, denied_tools, network_egress, quotas without editing the YAML file
  directly (form UI that writes back to keprix.yaml)

This is the operator's single entry point to all three enforcement layers (256, 257, 258)
per product, rather than requiring them to navigate to three separate admin sections for
each product.

---

#### Admin > Tool ACL  `/admin/tool-acl`

Prompt 256. Full audit log of tool ACL decisions across all products.
Cross-product view: operators can see denials across Aiva, ABBIS, and Petraclus in one table.
Filter by product, tool, decision, date.

---

#### Admin > Network Egress  `/admin/network-egress`

Prompt 257. Audit log of egress decisions: allowed and blocked outbound requests.
Filter by product, host, decision, tool name, date.

---

#### Admin > Quotas  `/admin/quotas`

Prompt 258. Per-product resource usage with progress bars.
Quota configuration per product (editable from here and from product detail).
Period reset controls.

---

#### Admin > Isolation Audit  `/admin/isolation-audit`

Prompt 259. Historical audit runs, finding list, run-now trigger, auto-fix trigger.

---

## Feature-to-entry-point map

This table maps every existing feature prompt to its UI location. Prompts without
an entry here are considered incomplete until they are mapped.

| Prompt | Feature | Primary entry point | Secondary entry points |
|--------|---------|--------------------|-----------------------|
| 245 | Twilio voice | `/voice` | `/settings/voice`, home discovery card |
| 246 | Brain graph API | (backend, surfaces via 247) | - |
| 247 | Brain graph canvas | `/brain/graph` | home card, session "view in brain" |
| 248 | Brain node content panel | Slide-in from `/brain/graph` | session context strip |
| 249 | Brain filter/search | Toolbar on `/brain/graph` | - |
| 250 | Brain live activation | Overlay on `/brain/graph` (auto, during session) | - |
| 251 | Brain layout engine | Layout selector on `/brain/graph` toolbar | - |
| 252 | Brain health dashboard | `/brain/health` | home discovery card |
| 253 | Brain session replay | `/brain/replay/[sessionId]` | session card, brain graph node |
| 254 | Brain export/share | Export menu on `/brain/graph` toolbar | brain sub-nav "Export" tab |
| 255 | Product namespace isolation | (backend, surfaces as security, no direct UI) | Isolation audit for operators |
| 256 | Tool ACL | `/admin/tool-acl` + `/admin/products/[id]` | keprix.yaml (developer) |
| 257 | Network egress | `/admin/network-egress` + `/admin/products/[id]` | keprix.yaml (developer) |
| 258 | Quotas + fairness scheduler | `/admin/quotas` + `/settings/billing` | sidebar quota bar |
| 259 | Isolation verifier | `/admin/isolation-audit` | keprix CLI |

---

## Empty state rules

Every page must have an empty state. Empty states must:

1. Name what the section is for in plain language (not "No data found")
2. Tell the user what action will fill it
3. Offer one primary action button
4. Optionally offer a contextual example or suggestion

Empty states must NOT:
- Show a generic illustration with no explanation
- Use technical jargon (no "no entities", no "null state", no "N/A")
- Offer more than two actions (one primary, one secondary maximum)

---

## Discovery trigger rules

A discovery trigger is a contextual prompt that tells the user a feature exists.
Triggers appear on the home page discovery card or as an inline session strip.

Rules:
- One active trigger at a time on the home page
- Triggers are evaluated in priority order: quota warnings first, then health, then discovery
- A dismissed trigger does not reappear for 30 days
- A trigger that has been acted on (user visited the target page) does not reappear

Priority order:
1. Quota > 80% (billing urgency)
2. Brain health score < 60 (data hygiene)
3. Brain not visited and memories >= 10 (feature discovery)
4. Skills = 0 and sessions >= 5 (feature discovery)
5. Voice not provisioned and workspace >= 30 days old (feature discovery)
6. Tasks completed and no playbooks (feature discovery)

---

## Rules for future prompts

When writing any future keprix feature prompt, the prompt MUST include a section:

```
## UI entry point

Primary location: [path and section name from the architecture above]
Secondary locations: [list or "none"]
Empty state: [what the user sees before data exists]
Discovery trigger: [condition + card text + action, or "none - operator feature"]
Nav placement: [which nav section this appears under, or "admin only"]
```

If a feature requires a new top-level nav section, the prompt must justify it and
update the architecture table in this document.

Features that are operator-only (admin layer) must explicitly state "operator only --
not shown to product surface users." They still need an entry point within the admin
section, but do not need a home discovery card.
