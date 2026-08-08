# Keprix - Prompt 217: Email OTP Step-Up

## Purpose

Add **email one-time passwords (OTP)** as a login and step-up option distinct from
TOTP authenticator apps. Useful when users have no 2FA app or SMTP is the primary trust channel.

## Already built (do not reimplement)

| Area | Location |
| --- | --- |
| TOTP 2FA | Prompt 216 (or existing API if 216 not done) |
| SMTP delivery | Invite and password reset email helpers |
| Rate limiting | `security/rate_limiter.py` |

## Gap

No email OTP challenge store. No "Send me a code" login path. No OTP for sensitive
account actions (disable 2FA, revoke sessions) when TOTP not available.

## Working directory

`/opt/lampp/htdocs/verlox/keprix/`

## Reference (read only)

- `prompts-archive/ref-213-account-security-architecture-reference.md`

## Step 1: OTP challenge store

Create `src/keprix/auth/otp_store.py`:

```python
@dataclass
class OtpChallenge:
    id: str
    user_id: str
    purpose: str  # login | step_up | password_reset_fallback
    code_hash: str
    expires_at: float
    attempts: int

def create_otp(user_id: str, purpose: str, *, ttl_minutes: int = 10) -> tuple[str, str]: ...
def verify_otp(challenge_id: str, code: str, *, max_attempts: int = 5) -> str | None: ...
```

- 6-digit numeric code (crypto RNG).
- Persist `{data_dir}/otp_challenges.json`; prune expired on read.

## Step 2: Backend routes

| Route | Purpose |
| --- | --- |
| `POST /api/auth/otp/send` | `{ username or email, purpose }` rate limit 5/hour/IP |
| `POST /api/auth/otp/verify` | `{ challenge_id, code }` returns session token when purpose=login |

For `purpose=login`:

1. After password verified (or on forgot-password alternative path), optionally offer OTP instead of TOTP when user has no TOTP.
2. Or: passwordless OTP login when `KEPRIX_OTP_LOGIN=true` (env flag, default false).

Email body: code + expiry + IP hint; no magic link (keep separate from password reset).

For `purpose=step_up`:

- Short-lived verification token returned; required header on sensitive routes for next 5 minutes.

## Step 3: Config

Add to `auth/config.py`:

```python
def otp_login_enabled() -> bool: ...
def otp_step_up_enabled() -> bool: ...
```

Env: `KEPRIX_OTP_LOGIN`, `KEPRIX_OTP_TTL_MINUTES`.

Expose in `GET /api/auth/config` as `otp_login_enabled`.

## Step 4: Frontend

**Login flow** (`LoginForm.tsx`):

- When `otp_login_enabled` or user clicks "Email me a sign-in code":
  - Step 1: email/username
  - Step 2: enter 6-digit code
- Reuse OTP input component (6 boxes or single field).

**Step-up modal** (`StepUpOtpDialog.tsx`):

- Used before disable 2FA or revoke all sessions when TOTP not enabled.
- Calls send + verify; stores step-up token in sessionStorage.

Page: document under `/settings/account/two-factor` as alternative method (read-only note if TOTP preferred).

## Step 5: Tests

- `tests/auth/test_otp_login.py`: send, verify, expiry, max attempts, rate limit.
- `tests/auth/test_otp_step_up.py`: step-up token gates protected action.

## Acceptance criteria

| # | Test |
| --- | --- |
| 1 | OTP email sent for valid user (or logged when SMTP off) |
| 2 | Valid code completes login when OTP login enabled |
| 3 | Invalid/expired codes rejected; attempts capped |
| 4 | Step-up OTP allows disable 2FA without TOTP enrolled |
| 5 | Rate limits enforced |
| 6 | `pytest tests/auth/test_otp_login.py` passes |

## Dependencies

- Prompt 215 (email infrastructure).
- Prompt 216 (2FA page hosts OTP alternative copy).

## Archive

`prompts-archive/` when AC pass.
