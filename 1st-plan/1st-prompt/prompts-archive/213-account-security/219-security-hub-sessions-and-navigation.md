# Keprix - Prompt 219: Security Hub, Active Sessions, and Navigation

## Purpose

Unify account security into a **Security hub** at `/settings/account`: profile, password,
2FA, SSO, and **active sessions**. Wire avatar menu and settings index. Polish the
user profile manager experience end-to-end.

## Already built (do not reimplement)

| Area | Location |
| --- | --- |
| Profile page | Prompt 214 |
| Password pages | Prompt 215 |
| 2FA page | Prompt 216 |
| OTP step-up | Prompt 217 |
| SSO connected accounts | Prompt 218 |
| Session storage | `auth/session.py` `_sessions` with expiry |
| Avatar menu shortcuts | `TopBar.tsx` (Settings, Messaging, etc.) |

## Gap

No unified account hub. Users cannot see or revoke other sessions. No `device_label`
on login. Avatar menu lacks "Account" entry pointing to security hub.

## Working directory

`/opt/lampp/htdocs/verlox/keprix/`

## Reference (read only)

- `prompts-archive/ref-213-account-security-architecture-reference.md`

## Step 1: Session metadata and list API

Extend `create_session()` to accept and store:

```python
device_label: str | None  # from User-Agent parse or client hint
ip_address: str | None
last_seen_at: float
session_id: str  # uuid; token remains opaque
```

Add `AuthManager` methods:

```python
def list_sessions(user_id: str) -> list[dict]: ...
def revoke_session(user_id: str, session_id: str) -> bool: ...
def revoke_all_sessions(user_id: str, except_token: str | None = None) -> int: ...
```

Routes:

- `GET /api/auth/sessions` - current user's sessions; mark current session.
- `DELETE /api/auth/sessions/{session_id}` - revoke one.
- `POST /api/auth/sessions/revoke-others` - keep current only.

Audit: `session_revoked`, `sessions_revoked_all`.

Optional: bump `last_seen_at` on authenticated requests (middleware hook, throttled).

Pass `X-Client-Label` header from frontend on login for friendly names ("Chrome on Linux").

## Step 2: Security hub layout

Create `frontend/src/app/(workspace)/settings/account/layout.tsx`:

- Side nav or tabs:
  - Profile (`/settings/account/profile`)
  - Password (`/settings/account/password`)
  - Two-factor (`/settings/account/two-factor`)
  - Connected accounts (`/settings/account/connected-accounts`)
  - Sessions (`/settings/account/sessions`)
- Hub landing `/settings/account` redirects to profile or shows overview cards with status:
  - 2FA on/off
  - SSO linked count
  - Active sessions count

Components: `AccountNav.tsx`, `SecurityOverviewCard.tsx`.

## Step 3: Sessions page

`/settings/account/sessions/page.tsx`:

- Table: device label, IP (masked partial), last seen, created, "This device" badge.
- Revoke button per row (not current).
- "Sign out all other devices" button with confirm dialog.
- Step-up OTP/TOTP if 217/216 require for bulk revoke.

## Step 4: Navigation polish

**TopBar avatar menu** (`TopBar.tsx`):

- Add "Account" link to `/settings/account` near top (below email/role).
- Keep existing Settings, Messaging, Notifications shortcuts.

**Settings index** (`settings/page.tsx`):

- Replace or supplement Prompt 214 card with primary **Account and security** card
  pointing to `/settings/account` (hub, not profile only).

**Mobile:** ensure account nav collapses to select dropdown.

## Step 5: Login session label

On `signIn`, send optional header:

```typescript
headers: { "X-Client-Label": navigator.userAgent.slice(0, 120) }
```

Backend parses coarse device string if label absent.

## Step 6: Tests

- `tests/auth/test_session_list.py`: list, revoke one, revoke others, current survives.
- `tests/frontend/test_security_hub.py`: layout routes resolve; overview shows totp flag.

## Acceptance criteria

| # | Test |
| --- | --- |
| 1 | User sees all active sessions on sessions page |
| 2 | Revoking another session invalidates that token |
| 3 | Revoke-others keeps current session |
| 4 | Account hub nav links all sub-pages |
| 5 | Avatar menu includes Account link |
| 6 | Settings index promotes Account and security |
| 7 | `pytest tests/auth/test_session_list.py` passes |
| 8 | Series docs updated (`authentication.md`, architecture reference status table) |

## Dependencies

- Prompts 214-218 (sub-pages must exist; stub pages OK during parallel dev).

## Archive

`prompts-archive/` when AC pass. Update
`prompts-archive/ref-213-account-security-architecture-reference.md` implementation status table.
