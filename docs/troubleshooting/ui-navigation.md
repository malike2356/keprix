# UI navigation troubleshooting

## Symptom: Sidebar item, tab, or card click does nothing

**Likely cause:** The browser soft-navigation path stuck, or an old frontend build still used MUI `component={Link}` from Next.js (known to drop clicks in the workspace shell).

**Fix:**

1. Hard-refresh the page (Ctrl+Shift+R / Cmd+Shift+R).
2. Open the destination URL directly in the address bar (for example `/outreach/leads`, `/crm/pipeline`).
3. Confirm you are on a recent build: Settings or footer should show Community Edition version; Contabo app should be rebuilt after frontend fixes.
4. If only one control fails, report the page URL and control label; if many fail, clear site data for the app origin and sign in again.

**Related:** Sidebar and section tabs use plain HTML anchors (`component="a"`). Developer policy: `frontend/src/components/ui/muiNavAnchor.ts`.

## Symptom: Outreach section tabs (Overview, Pipeline, Leads, …) do not open pages

**Fix:** Hard-refresh `/outreach`. Tabs should navigate to `/outreach/pipeline`, `/outreach/leads`, and sibling routes. See [Soft Wall and outreach](soft-wall-and-outreach.md).

## Symptom: Channel cards on `/outreach/channels` do not open

**Expected destinations:**

| Card | Route |
| --- | --- |
| Email Soft Wall | `/outreach/approvals` |
| Review Gateway | `/review-gateway` |
| Companies House | `/outreach/companies-house` |
| Mailbox | `/email` |
| Companies House (standalone) | `/companies-house` |

**Fix:** Hard-refresh; open the route from the table if a card still fails.

## Symptom: CRM overview cards do nothing

**Fix:** Hard-refresh `/crm`. Cards should open the matching `/crm/...` section. See [Agentic CRM](agentic-crm.md).

## Symptom: Agent OS subnav tabs stuck

**Fix:** Hard-refresh `/agent-os/glass`. Tabs should open Glass, Board, Onboarding, Memory, Usage via real anchors.
