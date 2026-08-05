# Keprix - Prompt 215: Password Change and Forgot Reset

## Purpose

Ship **logged-in password change** and **forgot-password email reset** so users can
recover access without admin help. Required before SSO linking (218) and 2FA disable flows.

## Already built (do not reimplement)

| Area | Location |
| --- | --- |
| Password hashing | `_hash_password`, `_verify_password` in `auth/session.py` |
| Invite set password | `set_password_and_approve()` in session |
| Rate limiting | `security/rate_limiter.py` |
| SMTP email | `auth/user_invites.py` `_send_invite_email` pattern |
| Login | `POST /api/auth/login` |

## Gap

No change-password route. No forgot/reset token flow. Login form has no "Forgot password?" link.

## Working directory

`/opt/lampp/htdocs/verlox/keprix/`

## Reference (read only)

- `prompts-archive/ref-213-account-security-architecture-reference.md`

## Step 1: Password reset token store

Create `src/keprix/auth/password_reset_store.py`:

```python
def create_reset_token(user_id: str, *, ttl_hours: int = 1) -> str: ...
def consume_reset_token(raw_token: str) -> str | None: ...  # returns user_id
def invalidate_user_tokens(user_id: str) -> None: ...
```

- Store hashed tokens in `{data_dir}/password_reset_tokens.json`.
- Single-use; mark `used_at` on consume.
- Invalidate prior pending tokens when creating a new one for same user.

## Step 2: Backend routes

Add to `auth/routes.py` (or `auth/password_routes.py` included in app):

| Route | Body | Behavior |
| --- | --- | --- |
| `POST /api/auth/me/password` | `current_password`, `new_password` | Verify current; min 8 chars; audit `password_changed`; revoke other sessions optional flag |
| `POST /api/auth/password/forgot` | `email` or `username` | Rate limit 3/hour/IP; always return generic success; send email if user found |
| `POST /api/auth/password/reset` | `token`, `new_password` | Consume token; set password; audit `password_reset_completed` |

Reset URL: `{frontend}/auth/reset-password?token=...`

Email template: plain + HTML, same SMTP fallback as invites (log link when SMTP off).

## Step 3: AuthManager helpers

```python
def change_password(user_id: str, current: str, new: str) -> tuple[bool, str]: ...
def reset_password(user_id: str, new: str) -> None: ...
```

On reset: clear `totp_secret_pending`; optionally keep TOTP enabled (document choice: keep enabled).

## Step 4: Frontend pages

| Page | Path |
| --- | --- |
| Change password | `/settings/account/password` |
| Forgot password | `/auth/forgot-password` |
| Reset password | `/auth/reset-password` |

`ChangePasswordForm.tsx`: current + new + confirm; strength hint (min 8).

`ForgotPasswordForm.tsx`: email field; success message without leaking existence.

`ResetPasswordForm.tsx`: read `token` from query; new + confirm; redirect to login on success.

Add "Forgot password?" link on `LoginForm.tsx`.

## Step 5: Tests

- `tests/auth/test_password_change.py`: happy path; wrong current password 401.
- `tests/auth/test_password_reset.py`: token single-use; expired token rejected; rate limit on forgot.

## Acceptance criteria

| # | Test |
| --- | --- |
| 1 | Logged-in user changes password with correct current password |
| 2 | Forgot endpoint sends email (or logs) for known user |
| 3 | Reset token works once; second use fails |
| 4 | Login works with new password after reset |
| 5 | Audit events recorded |
| 6 | `pytest tests/auth/test_password_reset.py tests/auth/test_password_change.py` passes |

## Dependencies

- Prompt 214 recommended (account section nav); can ship standalone pages first.

## Archive

`prompts-archive/` when AC pass.
