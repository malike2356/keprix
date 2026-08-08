# keprix - Prompt 22: Unified UI/UX Design System And App Shell

## Purpose

Create one unified Keprix UI/UX system that can absorb the best interaction patterns from Carina, Propreneur, TuinApp, OpenClaw, Hermes, and Odysseus without making the product feel fragmented.

The final product must feel professional, corporate, clean, premium, and consistent across web UI, mobile, desktop, TUI, CLI, embedded app surfaces, admin panels, and app-builder templates.

Do not merge four visual styles. Merge the best product patterns behind one Keprix design system.

## Core Direction

Keprix is the visual identity and product shell.

Use the reference products this way:

| Source | Adopt | Do Not Adopt |
| --- | --- | --- |
| Carina | Premium workspace identity, SaaS structure, governance, clean dashboards, app-builder direction. | Any Carina branding, commercial-only coupling, inconsistent legacy screens, or mixed branding. |
| Propreneur | Business workflow clarity, CRM-like records, client pipelines, forms, service operations, professional property-style density. | Property-only assumptions where the product is generic. |
| TuinApp | Marketplace and service-flow clarity, booking or request workflows, provider/customer role separation, operational status tracking. | Consumer-only styling where Keprix needs durable workspace trust. |
| OpenClaw | Multi-surface experience, mobile companion, command surfaces, canvas/live output, channel consistency. | Its visual brand or any playful styling that conflicts with Keprix. |
| Hermes | Power-user UX, TUI, task boards, worker/job visibility, diagnostics, model/provider controls. | Terminal-first complexity for normal users. |
| Odysseus | Workspace UX: documents, research, notes, calendar, gallery, model comparison, deep research, writing flows. | Any disconnected route-level UI that feels bolted on. |

## Non-Negotiable UX Rule

Keprix must feel like the same product everywhere.

The web UI, mobile app, desktop app, TUI, CLI, embedded app shell, Telegram/WebChat cards, approval cards, billing screens, app-builder templates, and admin views must share:

- Same terminology.
- Same information architecture.
- Same status language.
- Same command naming.
- Same icon logic.
- Same color roles.
- Same approval patterns.
- Same empty-state tone.
- Same error tone.
- Same layout hierarchy where the surface allows it.
- Same trust and safety signals.

Mobile can reflow and simplify. It must not become a different product.

## Product Personality

The interface should feel:

- Professional.
- Corporate.
- Clean.
- Premium.
- Calm.
- Useful.
- Direct.
- Warm without being chatty.
- Operationally serious.
- Trustworthy for finance, data, legal, research, healthcare, and business workflows.

Avoid:

- Playful SaaS decoration.
- Oversized marketing-style cards inside the product.
- Decorative blobs, orbs, and gradients.
- Random icon styles.
- Emoji.
- Fluffy helper text.
- AI-looking typography.
- Dense clutter without hierarchy.
- Separate visual identities per app.

## App Shell

Build one Keprix shell used by web, desktop, mobile, and embedded apps.

Primary zones:

- Workspace switcher.
- Product or app switcher.
- Global command palette.
- Agent status.
- Scout or safety status.
- Notifications.
- Search.
- Current user and role.
- Primary navigation.
- Current task/job area.
- Main content.
- Right-side context panel where space allows.

Primary navigation groups:

- Workspace.
- Apps.
- Data.
- Research.
- Automations.
- Commerce.
- Security.
- Admin.

Each product built on Keprix can hide irrelevant groups, but it must not invent a new navigation system.

## Main Modes

### Workspace

For daily work:

- Chat.
- Documents.
- Notes.
- Files.
- Calendar.
- Email.
- Gallery.
- Memory.
- Tasks.

This mode adopts Odysseus workspace breadth and Keprix polish.

### Apps

For products built on Keprix:

- App dashboard.
- Records.
- Customer or user flows.
- App-specific tools.
- App settings.
- App analytics.
- App billing where enabled.

This mode adopts Propreneur and TuinApp business workflow clarity.

### Data

For analytics, datasets, statistical workflows, and ML:

- Dataset catalog.
- Imports.
- Profiles.
- Variables.
- Codebooks.
- Analysis runs.
- Charts.
- Reports.
- ML experiments.
- Model registry.

This mode supports SPSS, PSPP, jamovi, R, Python, DuckDB, Parquet, and spreadsheet workflows from Prompts 32 and 74-83.

### Research

For deep research and knowledge work:

- Research projects.
- Sources.
- Claims.
- Citations.
- Literature notes.
- Obsidian export.
- Contradictions.
- Reports.
- Review queue.

This mode must make provenance visible without overwhelming normal users.

### Automations

For agent jobs and operations:

- Job queue.
- Worker status.
- Schedules.
- Approvals.
- Run history.
- Logs.
- Retries.
- Dead-letter items.

This mode adopts Hermes job visibility, but presents it with Keprix clarity.

### Commerce

For SaaS and app monetization:

- Products.
- Plans.
- Checkout.
- Subscriptions.
- Entitlements.
- Usage.
- Revenue.
- Invoices.
- Payment providers.

This mode follows Prompt 30.

### Security

For trust and control:

- Scout status.
- Audit logs.
- Policies.
- Vault.
- Credential setup.
- Risk queue.
- Approval history.
- Cyber authorization.
- Compliance exports.

This mode must always be clear, sober, and permission-aware.

### Admin

For owners and operators:

- Users.
- Roles.
- Workspaces.
- Integrations.
- System health.
- Configuration.
- Backup.
- Import/export.
- Diagnostics.

Admin surfaces must be dense but organized, with tables, filters, and clear status chips.

## Design System Tokens

Define shared tokens for all surfaces:

```text
ui/tokens/
  colors.json
  typography.json
  spacing.json
  radius.json
  shadows.json
  motion.json
  status.json
  icons.json
```

Use `/opt/lampp/htdocs/verlox/keprix/keprix/ui/theme-switcher-css/` as the
source library for theme switcher CSS and named theme packs. Normalize those
CSS files into Keprix tokens before using them in React, mobile, desktop, or
embedded app surfaces. Theme names may be reused, but colors, states, and
interaction behavior must be expressed through the shared token system.

Rules:

- Use one neutral base palette with disciplined accent colors.
- Avoid one-note color themes.
- Use color by semantic role: primary, success, warning, danger, info, muted, surface, border, focus.
- Use 8px radius or less unless a native platform requires otherwise.
- Use compact, readable typography.
- Do not scale font size with viewport width.
- Use consistent spacing steps.
- Use motion only for state changes, loading, progress, and focus, not decoration.

## Component System

Build shared components:

```text
ui/components/
  AppShell
  Sidebar
  TopBar
  CommandPalette
  WorkspaceSwitcher
  AppSwitcher
  StatusPill
  DataTable
  FilterBar
  RecordDetail
  Timeline
  ApprovalCard
  RiskBanner
  JobCard
  UsageMeter
  PlanCard
  CheckoutSummary
  DatasetPreview
  VariableTable
  ResearchSourceCard
  ClaimCard
  CitationList
  ObsidianExportPanel
  ModelRunCard
  ToolRunTrace
  EmptyState
  ErrorState
  MobileActionSheet
  TuiPanelSpec
```

Every component must have:

- Web implementation.
- Mobile mapping.
- Desktop mapping where applicable.
- TUI/CLI text equivalent where applicable.
- Empty state.
- Loading state.
- Error state.
- Permission-denied state.
- Audit or risk state where applicable.

## Cross-Surface Consistency

Define a shared UI contract so different clients render the same product state.

```text
backend/ui_contract/
  navigation.py
  actions.py
  statuses.py
  cards.py
  tables.py
  forms.py
  approvals.py
  errors.py
  empty_states.py
  schemas.py
```

The backend should expose structured UI descriptors for:

- Navigation groups.
- Feature flags.
- User role.
- Workspace state.
- App state.
- Available actions.
- Required approvals.
- Risk level.
- Job status.
- Billing state.
- Setup state.
- Localization state.

Clients may choose native rendering, but must use the same names, states, and action contracts.

## Web UI

The web UI is the full product surface.

Requirements:

- Responsive app shell.
- Dense but clean dashboards.
- Tables with filters and saved views.
- Split panes for workspace flows.
- Right-side context panel for agent, source, job, or record context.
- Command palette for fast navigation and actions.
- Consistent approval cards.
- Consistent setup and credential flows.
- Consistent billing and checkout patterns.
- Consistent data and research workspaces.

Web must set the standard that mobile and desktop adapt from.

## Mobile UI

Mobile is not a simplified separate product. It is Keprix optimized for field use and approval.

Requirements:

- Same navigation groups, collapsed into tabs or drawers.
- Same status language.
- Same command concepts.
- Fast approval and review.
- Voice input and voice output.
- Camera and file capture.
- Offline-tolerant drafts where possible.
- Job and alert notifications.
- Compact record views.
- Safe credential handoff.

Mobile should prioritize:

- Chat.
- Approvals.
- Notifications.
- Field data capture.
- Voice.
- App-specific workflows.
- Quick status checks.

Advanced admin and analytics can open compact views or deep links to web, but the user must not feel moved into another brand.

## Desktop UI

Desktop should wrap or extend the web UI without changing the design language.

Requirements:

- Same app shell.
- Native file integration.
- Local folder and Obsidian vault access.
- Local dataset handling.
- Desktop notifications.
- Optional local model controls.
- Secure local credential handoff.

## TUI And CLI

The TUI and CLI should be professional power surfaces, not separate products.

Requirements:

- Same command names as web and mobile.
- Same status terms.
- Same risk and approval labels.
- Same role and permission wording.
- Same job states.
- Same setup flow language.
- Same plain language errors.

TUI screens:

- Dashboard.
- Jobs.
- Providers.
- Tools.
- Data imports.
- Research runs.
- Approvals.
- Logs.
- System health.

CLI commands should mirror slash commands where practical.

## Embedded App Surfaces

Apps built on Keprix must inherit the shell and design system.

Each app should declare:

```yaml
app_ui:
  app_name: Borehole Advisor
  navigation:
    - dashboard
    - records
    - jobs
    - reports
    - billing
    - settings
  primary_record: borehole_project
  accent_role: field_services
  enabled_modules:
    - workspace
    - data
    - commerce
    - research
```

The app can have domain-specific screens, but it must use Keprix components, Keprix status language, Keprix forms, Keprix approvals, and Keprix app-builder patterns.

## Visual Style

Define a premium but restrained style:

- Light-first interface with a serious dark mode.
- White or near-white content surfaces.
- Clear borders.
- Subtle shadows only where needed.
- Clean tables.
- Strong form alignment.
- Compact card radius.
- High contrast text.
- Small, useful icons.
- Clear status chips.
- Calm accent color use.

Avoid:

- Marketing hero layouts inside the app.
- Decorative gradients as the main product style.
- Huge rounded cards.
- One-color UI.
- Playful illustration-heavy workflows.
- Random dashboards that look like different templates.

## Information Architecture

Use a consistent hierarchy:

```text
Workspace
  App
    Mode
      View
        Record
          Action
```

Examples:

- Workspace -> Borehole Advisor -> Apps -> Projects -> Project Detail -> Request Site Survey.
- Workspace -> Core -> Research -> Project -> Source -> Add Citation.
- Workspace -> Core -> Data -> Dataset -> Variables -> Generate Codebook.
- Workspace -> Core -> Automations -> Jobs -> Job Detail -> Retry.

Breadcrumbs, page titles, command palette labels, and mobile headers must follow this hierarchy.

## Status Language

Use one shared status vocabulary:

- Draft.
- Ready.
- Running.
- Waiting.
- Needs approval.
- Blocked.
- Failed.
- Complete.
- Archived.
- Suspended.
- At risk.
- Over limit.
- Synced.
- Out of sync.

Do not invent per-module variants unless absolutely needed.

## Approval UX

Risky actions must look and behave the same everywhere.

Approval cards must show:

- Action.
- Requesting user or agent.
- Target.
- Data touched.
- Cost or financial impact.
- Risk level.
- Reversibility.
- Expiry time.
- Approve button.
- Reject button.
- View details.
- Audit link after completion.

This pattern applies to web, mobile, TUI, CLI, Telegram, Slack, Discord, and WebChat.

## Agent UX

The agent must feel present but not noisy.

Show:

- What the agent is doing.
- Current job or step.
- Tool being used.
- Awaiting approval state.
- Error or blocker.
- Final result.
- Source or artifact links.

Do not show:

- Raw chain-of-thought.
- Excessive internal logs to normal users.
- Random model/provider details unless the user is in advanced mode.

Advanced users can open traces, tool output, model routing, cost, and retries.

## Data, Research, And ML UX

The data and research workspace must feel integrated with the rest of Keprix.

Requirements:

- Dataset preview uses the same table component as CRM records.
- Variable tables use the same filter and status components.
- Research source cards use the same record-detail layout.
- Claims and citations use the same timeline and audit patterns.
- ML experiments use the same job and artifact components.
- Reports use the same export panel as commerce and admin exports.
- Obsidian export uses the same setup and confirmation pattern as file export.

This prevents the data science area from feeling like a separate tool pasted into the app.

## Localization And Accessibility

Every UI surface must support:

- Localization from Prompt 27.
- Right-to-left layout where required.
- Voice input.
- Voice output where supported.
- Keyboard navigation.
- Screen reader labels.
- High contrast mode.
- Reduced motion.
- Clear focus states.
- Text that fits on mobile.

Localized UI must preserve the same information architecture and action names.

## Output Paths

Use these target paths unless the codebase evolves before implementation:

```text
keprix/ui/design-system/
  tokens/
  components/
  patterns/
  icons/
  content/
  accessibility/

keprix/ui/web/
  app-shell/
  workspace/
  apps/
  data/
  research/
  automations/
  commerce/
  security/
  admin/

keprix/ui/mobile/
  app-shell/
  screens/
  components/
  navigation/

keprix/ui/desktop/
  shell/
  native-bridges/

keprix/ui/tui/
  screens/
  components/
  keybindings/

keprix/backend/ui_contract/
keprix/tests/ui/
```

## App Builder Templates

Every generated app should inherit:

- App shell.
- Navigation contract.
- Record list.
- Record detail.
- Form builder.
- Status timeline.
- Task/job panel.
- Approval card.
- Billing page.
- Usage dashboard.
- Settings.
- Audit trail.
- Support page.

Generated apps must not create a new design language unless the user explicitly creates a white-label brand. Even white-label apps should keep the Keprix interaction model.

## Tests

Add tests for:

- Web and mobile navigation expose the same top-level groups for the same role.
- Web and mobile use the same status labels.
- Approval cards show the same required fields across web, mobile, and chat.
- Command palette and slash commands use the same action names.
- App-builder templates use the shared components.
- Data, research, commerce, and admin pages share the same table and filter patterns.
- Localization does not break navigation labels or button text.
- Long labels fit on mobile.
- Role-based hidden modules are consistent across surfaces.
- TUI job states match web job states.
- CLI errors match web setup errors in meaning and tone.
- No UI text contains emoji, em dash, en dash, or forbidden typography.

## Acceptance Criteria

- Keprix has one documented UI/UX design system.
- Web, mobile, desktop, TUI, CLI, embedded apps, and chat cards use the same product language.
- The visual identity is Keprix-first: professional, corporate, clean, premium, and calm.
- Propreneur and TuinApp influence business workflows without changing Keprix's visual identity.
- OpenClaw influences multi-surface interaction without changing Keprix's visual identity.
- Hermes influences power-user operations without overwhelming normal users.
- Odysseus influences workspace breadth without creating disconnected screens.
- Apps built on Keprix inherit the same shell, navigation logic, status vocabulary, approval UX, billing patterns, and data/reporting components.
- Mobile feels like Keprix, not a different product.
- Advanced functionality is discoverable through progressive disclosure.
- Every UI surface follows the seven engineering pillars.
