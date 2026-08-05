# Keprix - Prompt 214: Account Profile API and UI

## Purpose

Ship **self-service account profile** so every signed-in user can view and update
their identity fields without admin intervention. Foundation for the security hub
(Prompt 219).

## Already built (do not reimplement)

| Area | Location |
| --- | --- |
| Current user read | `GET /api/auth/me`, `_public_user()` in `auth/routes.py` |
| User storage | `AuthManager` in `auth/session.py` |
| Session context | `frontend/src/lib/ce-auth.tsx`, `CEUser` in `ce-api.ts` |
| Settings shell | `frontend/src/app/(workspace)/settings/page.tsx` |
| Admin user email update | `PUT /api/admin/users/{id}` (admin only) |

## Gap

No `PATCH /api/auth/me`. No profile page. Users cannot change display name, email,
or preferences. Avatar menu shows email but no link to edit profile.

## Working directory

`/opt/lampp/htdocs/verlox/keprix/`

## Reference (read only)

- `prompts-archive/ref-213-account-security-architecture-reference.md`

## Step 1: Backend profile update

Add to `auth/session.py`:

```python
def update_profile(
    user_id: str,
    *,
    display_name: str | None = None,
    email: str | None = None,
    avatar_url: str | None = None,
    locale: str | None = None,
    timezone: str | None = None,
) -> dict[str, Any] | None: ...
```

Rules:

- Validate email format; normalize to lowercase.
- If email changes, optionally require uniqueness across users (reject duplicate).
- `display_name` defaults to username when unset in `_public_user`.
- Persist to `users.json`; thread-safe with existing locks.

Add `PATCH /api/auth/me` in `auth/routes.py`:

```python
class ProfileUpdateRequest(BaseModel):
    display_name: str | None = Field(None, max_length=120)
    email: str | None = None
    avatar_url: str | None = Field(None, max_length=2048)
    locale: str | None = Field(None, max_length=16)
    timezone: str | None = Field(None, max_length=64)
```

Extend `_public_user()` to include new fields.

Audit: `profile_updated` with changed field names (not values for email).

## Step 2: Frontend API client

Create `frontend/src/lib/account-api.ts`:

- `fetchAccountProfile()` -> `GET /api/auth/me`
- `updateAccountProfile(payload)` -> `PATCH /api/auth/me`

Refresh `SessionProvider` user after successful PATCH (call `setCESession` with updated user).

## Step 3: Profile page

Create `frontend/src/app/(workspace)/settings/account/profile/page.tsx`:

- Form: display name, email, avatar URL (text), locale (select: en, fr, etc.), timezone (select or text).
- Read-only: username, role, member since (`created_at` if exposed).
- Save button with success/error alerts.
- Use existing MUI patterns from `/settings/notifications`.

Optional layout wrapper `settings/account/layout.tsx` with section nav (stub tabs for 215-219).

## Step 4: Settings discoverability

Add card to `settings/page.tsx`:

```text
Account and profile
View and update your name, email, and preferences.
href: /settings/account/profile
```

Not admin-only.

## Step 5: Tests

- `tests/auth/test_profile_update.py`: PATCH updates fields; duplicate email rejected; audit called.
- `tests/frontend/test_account_profile.py`: smoke import of profile page module.

## Acceptance criteria

| # | Test |
| --- | --- |
| 1 | `PATCH /api/auth/me` updates display_name and email for authenticated user |
| 2 | Duplicate email returns 400 |
| 3 | Profile page loads and saves; session user refreshes |
| 4 | Settings index shows Account card |
| 5 | `pytest tests/auth/test_profile_update.py` passes |

## Dependencies

- Prompt 213 reference (read only).

## Archive

`prompts-archive/` when AC pass.
