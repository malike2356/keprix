# Good first issues (maintainer seed list)

Keep at least five open issues labeled `good-first-issue`. Use these templates
when the queue runs low.

## 1. Frontend: redirect to legal gate on HTTP 451

**Acceptance criteria**

- `ceApi` detects HTTP 451 `legal_acceptance_required` responses.
- User is redirected to `/legal/accept` with return URL preserved.
- Manual test: block API call before acceptance, accept policies, return to app.

## 2. Review gateway: link export file in create form

**Acceptance criteria**

- Review gateway create UI accepts an export `file_id` from `/api/export`.
- Artifact renders as PDF embed on the public review page.
- Test: create export, create review request, open public link, approve.

## 3. Analytics: jamovi plan preview panel

**Acceptance criteria**

- Analytics page calls `POST /api/analytics/jamovi/plan` after export.
- UI shows analysis steps and generated R script in a read-only panel.
- `pnpm build` passes.

## 4. Browser: document Playwright enablement path

**Acceptance criteria**

- Add `docs/developer/browser-driver.md` describing how to swap `StubBrowserDriver` for Playwright.
- No code change required beyond docs and a config flag stub if missing.
- `scripts/validate-community-files.sh` still passes.

## 5. Privacy: export acceptance log CSV from settings

**Acceptance criteria**

- Settings page button downloads `/api/legal/acceptances/export` for admins.
- Non-admin users do not see the control.
- Error state shown when download fails.
