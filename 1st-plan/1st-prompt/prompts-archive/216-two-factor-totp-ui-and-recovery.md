# Keprix - Prompt 216: Two-Factor Authentication (TOTP UI and Recovery Codes)

## Purpose

Wire existing **TOTP backend** to a complete **2FA enrollment UI**, **login step**,
and **backup recovery codes**. Closes the gap between API-only 2FA and usable product security.

## Already built (do not reimplement)

| Area | Location |
| --- | --- |
| TOTP crypto | `auth/totp.py` (pyotp, encrypt at rest) |
| Setup/verify/disable API | `POST /api/auth/totp/setup|verify|disable` |
| Login with code | `LoginRequest.totp_code`, `totp_verify()` in session |
| Env force 2FA | `KEPRIX_REQUIRE_2FA` documented in `docs/security/architecture.md` |

## Gap

No UI to enroll 2FA. Login form does not collect TOTP when required. No recovery codes
if user loses authenticator app.

## Working directory

`/opt/lampp/htdocs/verlox/keprix/`

## Reference (read only)

- `prompts-archive/ref-213-account-security-architecture-reference.md`

## Step 1: Recovery codes (backend)

Extend `AuthManager`:

```python
def generate_recovery_codes(username: str, *, count: int = 10) -> list[str]: ...
def consume_recovery_code(username: str, code: str) -> bool: ...
```

- Store bcrypt hashes of normalized codes (format: `XXXX-XXXX` display).
- Return plain codes once on generate; invalidate previous set.
- `consume_recovery_code` used at login when `totp_code` fails but `recovery_code` provided.

Add routes:

- `POST /api/auth/totp/recovery/generate` (requires password re-check or recent session + TOTP enabled)
- Extend login body: optional `recovery_code: str | None`

Audit: `recovery_code_used`, `recovery_codes_regenerated`.

## Step 2: Login two-step UI

Update `LoginForm.tsx` and `ce-auth.tsx` / `loginWithCredentials`:

1. First submit: username + password only.
2. If API returns `401` with detail `"Invalid two-factor code"` OR new response shape
   `{ requires_totp: true }`, show second step (6-digit TOTP + optional "Use recovery code" toggle).
3. Resubmit with `totp_code` or `recovery_code`.

Prefer explicit `403` or structured error from backend when password OK but TOTP missing:

```python
# Option: split login into challenge endpoint, or return 401 with code "totp_required"
```

Document chosen approach in `authentication.md`.

## Step 3: Two-factor settings page

Create `/settings/account/two-factor/page.tsx`:

**Disabled state:**

- Explain TOTP; "Enable two-factor" button.
- On enable: call `POST /api/auth/totp/setup`; show QR (`qrcode.react` or img from provisioning URI API).
- Show manual secret; input to confirm 6-digit code; call verify.
- On success: display recovery codes once with copy/download; checkbox "I saved these codes".

**Enabled state:**

- Status chip "2FA enabled".
- Regenerate recovery codes (confirm dialog + password).
- Disable 2FA: require TOTP code or recovery code + password.

Component: `TwoFactorSetupPanel.tsx`, `RecoveryCodesDialog.tsx`.

## Step 4: Admin visibility

On `/settings/users` (admin): show `totp_enabled` badge per user (read-only). Do not expose secrets.

Optional admin action: "Require 2FA reset" (clears TOTP; user must re-enroll) behind confirm; audit `admin_totp_reset`.

## Step 5: Tests

- `tests/auth/test_recovery_codes.py`: generate, consume once, regenerate invalidates old.
- `tests/auth/test_login_totp_flow.py`: login requires totp when enabled.
- Extend frontend smoke for two-factor page.

## Acceptance criteria

| # | Test |
| --- | --- |
| 1 | User enrolls TOTP via UI; `totp_enabled` true on `/api/auth/me` |
| 2 | Login requires valid TOTP after enroll |
| 3 | Recovery code works once at login |
| 4 | Disable 2FA requires valid code |
| 5 | Recovery codes shown only once on generate |
| 6 | `pytest tests/auth/test_recovery_codes.py` passes |

## Dependencies

- Prompt 215 (password re-check pattern for sensitive actions).

## Archive

`prompts-archive/` when AC pass.
