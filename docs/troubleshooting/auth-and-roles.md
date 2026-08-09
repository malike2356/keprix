# Auth and roles troubleshooting

## Symptom: Redirected to login or blank shell

**Fix:** Sign in again. Confirm cookies are allowed for the app origin. Check `/settings/account/sessions` after login.

## Symptom: Missing sidebar items another user can see

**Likely cause:** Role or feature-flag gating.

**Fix:** Compare role (admin/owner vs operator). Admins see Admin group. Feature flags and simplified mode can hide non-admin items. See [Navigation and roles](../features/navigation-and-roles.md) and `/admin/feature-flags` (admins).

## Symptom: Tool or Soft Wall action forbidden

**Fix:** Check Tool ACL (`/admin/tool-acl`) and Soft Wall approvals. Operator may lack grant for that tool or tenant.
