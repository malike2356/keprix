# Authentication

Sign-in, registration, roles, and onboarding for Keprix instances.

## Routes

| Route | Purpose |
| --- | --- |
| `/auth/login` | Username/password login |
| `/auth/register` | New user registration (when enabled) |
| `/auth/setup` | First-time instance setup |
| `/onboarding` | Post-login product tour |

## Roles

| Role | Access |
| --- | --- |
| `owner` | Full instance control, developer identity |
| `admin` | Dashboard, governance, user invite |
| `user` | Workspace tools, no admin dashboard |

Multi-user mode is controlled by environment flags. See [Environment variables](../configuration/environment-variables.md).

## Session

JWT/session cookies issued by `/api/auth/login`. Frontend uses `SessionProvider` and `ceApi` with credentials.

## First admin

Created during [First run](../getting-started/first-run.md) wizard or CLI `keprix setup`.

## API

| Action | Endpoint |
| --- | --- |
| Login | `POST /api/auth/login` |
| Register | `POST /api/auth/register` |
| Session | `GET /api/auth/me` |
| Logout | `POST /api/auth/logout` |

## Related

- [First run](../getting-started/first-run.md)
- [Admin dashboard](../operations/admin-dashboard.md)
