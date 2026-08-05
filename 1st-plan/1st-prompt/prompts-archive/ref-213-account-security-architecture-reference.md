# Keprix - Prompt 213: Account and Security Architecture Reference

## Purpose

Reference and dependency map for the **user profile manager** and **account security**
series. Build Prompts **214-219** in numeric order. **Do not archive this file.**

Prompt 213 is documentation only. Update this file when 214-219 land so later
work does not re-discover the same gaps.

---

## Implementation status (2026-07-06)

| Area | Status | Location |
| --- | --- | --- |
| Username/password login | **Shipped** | `src/keprix/auth/routes.py`, `frontend/src/components/auth/LoginForm.tsx` |
| Session tokens (cookie) | **Shipped** | `src/keprix/auth/session.py`, `keprix_session` cookie |
| TOTP backend (setup/verify/disable) | **Shipped** (no UI) | `POST /api/auth/totp/*`, `auth/totp.py` |
| Login with `totp_code` | **Shipped** (no UI step) | `LoginRequest.totp_code` in `auth/routes.py` |
| Workspace invites + accept | **Shipped** | `auth/user_invites.py`, `/auth/accept-invite` |
| Admin user CRUD | **Shipped** | `auth/admin_routes.py`, `/settings/users` |
| CLI dashboard OAuth (basic/nous/self_hosted) | **Shipped** (CLI only) | `keprix_cli/dashboard_auth/` |
| Self-service account profile | **Shipped** (Prompt 214) | `PATCH /api/auth/me`, `/settings/account/profile`, `account-api.ts` |
| Password change (logged in) | **Shipped** (Prompt 215) | `POST /api/auth/me/password`, `/settings/account/password` |
| Forgot password / email reset | **Shipped** (Prompt 215) | `password_reset_store.py`, `/auth/forgot-password`, `/auth/reset-password` |
| TOTP setup UI + QR + recovery codes | **Shipped** (Prompt 216) | `/settings/account/two-factor`, recovery codes, login 2FA step |
| Email/SMS OTP step-up | **Shipped** (Prompt 217) | `otp_store.py`, `/api/auth/otp/*`, `StepUpOtpDialog` |
| SSO on workspace login | **Shipped** (Prompt 218) | `auth/sso/`, `/api/auth/sso/*`, `/auth/sso/callback`, `/settings/account/connected-accounts` |
| Active sessions list / revoke others | **Shipped** (Prompt 219) | `session_routes.py`, `/api/auth/sessions`, `/settings/account/sessions` |
| Security hub and navigation | **Shipped** (Prompt 219) | `/settings/account`, `AccountNav`, TopBar Account link |

---

## Product scope

### In scope (Prompts 214-219)

1. **Account profile** - display name, email, avatar (URL or upload v1 URL-only), locale/timezone prefs.
2. **Password** - change while logged in; forgot-password email link; rate limits and audit.
3. **2FA (TOTP)** - enroll, QR/provisioning URI, confirm, disable, backup recovery codes (one-time).
4. **OTP step-up** - email (SMTP) one-time codes for login or sensitive actions when TOTP not enrolled.
5. **SSO** - OAuth/OIDC providers on workspace login (Google, GitHub, generic OIDC); link/unlink to local account.
6. **Security hub** - `/settings/account` shell, active sessions, navigation from avatar menu and settings index.

### Out of scope (defer)

| Item | Reason |
| --- | --- |
| LDAP/Active Directory | Enterprise tier; separate prompt if needed |
| SAML IdP | Enterprise tier |
| SMS OTP via Twilio | Optional env; email OTP is v1 |
| Passkeys/WebAuthn | Follow-on prompt after TOTP stable |
| Postgres auth migration | JSON `users.json` remains v1; wire SQL schema when fleet DB lands |

---

## Auth data model (today)

Users live in `{data_dir}/users.json` via `AuthManager` in `session.py`:

```text
id, username, email, password_hash, role, totp_enabled, totp_secret,
totp_secret_pending, is_approved, is_active, last_login_at, created_at
```

Sessions in `{data_dir}/sessions.json`:

```text
token -> { username, expiry, device_label?, created_at }
```

New stores for this series (suggested):

| Store | Purpose |
| --- | --- |
| `password_reset_tokens.json` | Hashed token, user_id, expires_at, used_at |
| `recovery_codes.json` or field on user | Hashed backup codes for TOTP |
| `otp_challenges.json` | Email OTP: hashed code, purpose, expires_at |
| `oauth_identities.json` | provider + subject -> user_id, link metadata |

Prefer extending `AuthManager` methods before new parallel managers. Keep file-backed
stores consistent with invites (`invite_store.py` pattern).

---

## API surface (target)

| Method | Path | Prompt | Auth |
| --- | --- | --- | --- |
| GET | `/api/auth/me` | exists | session |
| PATCH | `/api/auth/me` | 214 | session |
| POST | `/api/auth/me/password` | 215 | session + current password |
| POST | `/api/auth/password/forgot` | 215 | public, rate limited |
| POST | `/api/auth/password/reset` | 215 | public + token |
| POST | `/api/auth/totp/setup` | exists | session |
| POST | `/api/auth/totp/verify` | exists | session |
| POST | `/api/auth/totp/disable` | exists | session + code |
| GET | `/api/auth/totp/recovery` | 216 | session (regenerate) |
| POST | `/api/auth/totp/recovery/consume` | 216 | login fallback |
| POST | `/api/auth/otp/send` | 217 | public or session |
| POST | `/api/auth/otp/verify` | 217 | public or session |
| GET | `/api/auth/sessions` | 219 | session |
| DELETE | `/api/auth/sessions/{id}` | 219 | session |
| GET | `/api/auth/sso/providers` | 218 | public |
| GET | `/api/auth/sso/{provider}/start` | 218 | public |
| GET | `/api/auth/sso/callback` | 218 | public |
| POST | `/api/auth/sso/link` | 218 | session |
| DELETE | `/api/auth/sso/link/{provider}` | 218 | session |

---

## Frontend routes (target)

| Route | Prompt | Purpose |
| --- | --- | --- |
| `/settings/account` | 219 | Security hub overview cards |
| `/settings/account/profile` | 214 | Profile form |
| `/settings/account/password` | 215 | Change password |
| `/settings/account/two-factor` | 216 | TOTP enroll/disable + recovery |
| `/settings/account/sessions` | 219 | Active sessions |
| `/settings/account/connected-accounts` | 218 | SSO link/unlink |
| `/auth/forgot-password` | 215 | Request reset email |
| `/auth/reset-password?token=` | 215 | Set new password |
| `/auth/login` | 216, 217, 218 | TOTP step, OTP fallback, SSO buttons |

Wire avatar dropdown (`TopBar.tsx`) and settings index card for **Account and security** (shipped in Prompt 219).

---

## Security requirements (all prompts)

- Rate limit public endpoints (reuse `security/rate_limiter.py` keys: `auth_password_forgot`, etc.).
- Audit log: `profile_updated`, `password_changed`, `password_reset_requested`, `totp_enabled`, `totp_disabled`, `recovery_code_used`, `session_revoked`, `sso_linked`, `sso_login`.
- Never return password hashes, TOTP secrets, or plain recovery codes after first display.
- Reset and OTP tokens: `secrets.token_urlsafe(32)`, store `hash_token()` only.
- Require current password (or recent re-auth) before disable 2FA, link SSO, or view recovery codes.
- Email via existing SMTP path (`user_invites._send_invite_email` pattern).

---

## Dependencies on existing work

| Prompt / area | Why |
| --- | --- |
| 116 UI foundation | MUI settings patterns |
| Invite email SMTP | Password reset and OTP email delivery |
| `dashboard_auth` base | SSO provider interface for 218 |
| Security audit | `keprix.security.audit.audit_log` |
| TopBar avatar menu | Shortcuts to account settings |

---

## Build order

See `prompts-archive/ref-213-account-security-build-order.md`.

```
214 Account profile (API + UI)
  |
215 Password change + forgot reset
  |
216 TOTP UI + recovery codes (+ login 2FA step)
  |
217 Email OTP step-up (login + optional sensitive actions)
  |
218 SSO/OAuth workspace providers
  |
219 Security hub + sessions + navigation polish
```

---

## Acceptance criteria (series complete)

| # | Test |
| --- | --- |
| 1 | User updates profile email/name at `/settings/account/profile`; `GET /api/auth/me` reflects change |
| 2 | Forgot password sends email (or logs link when SMTP off); reset token works once |
| 3 | Logged-in user changes password; old password rejected |
| 4 | TOTP enroll shows QR; login requires code; recovery code works once |
| 5 | Email OTP login works when configured; rate limited |
| 6 | SSO login creates or links user; local password login still works if linked |
| 7 | User lists and revokes other sessions; current session survives unless revoked |
| 8 | All new backend tests pass; no stubs |
| 9 | Settings and avatar menu link to account hub |

---

## Related docs to update when series ships

- `docs/getting-started/authentication.md`
- `docs/security/architecture.md`
- `docs/configuration/environment-variables.md` (SSO client IDs, OTP TTL)
