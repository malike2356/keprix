# Keprix - Prompt 218: SSO and OAuth Workspace Login

## Purpose

Bring **OAuth/OIDC single sign-on** to the workspace web app (`/auth/login`), reusing
patterns from CLI `dashboard_auth` providers. Support Google, GitHub, and generic OIDC;
allow linking SSO identity to existing local accounts.

## Already built (do not reimplement)

| Area | Location |
| --- | --- |
| Dashboard auth plugin protocol | `keprix_cli/dashboard_auth/base.py` |
| Basic / Nous / Self-hosted providers | `plugins/dashboard_auth/*` |
| OAuth callback routes (CLI) | `keprix_cli/dashboard_auth/routes.py` |
| Session creation | `auth_manager.create_session()` |
| Profile email | Prompt 214 |

## Gap

Workspace login is username/password only. SSO exists for CLI dashboard, not Next.js app.
No linked identities store. No "Continue with Google" on login page.

## Working directory

`/opt/lampp/htdocs/verlox/keprix/`

## Reference (read only)

- `prompts-archive/ref-213-account-security-architecture-reference.md`
- `src/keprix/keprix_cli/dashboard_auth/base.py` (read patterns, do not import CLI routes in frontend)

## Step 1: Workspace SSO module

Create `src/keprix/auth/sso/`:

```
sso/
  __init__.py
  registry.py      # register providers from config
  store.py         # oauth_identities.json: provider+sub -> user_id
  providers/
    google.py
    github.py
    oidc_generic.py
```

Each provider implements:

```python
def authorization_url(state: str, redirect_uri: str) -> str: ...
async def exchange_code(code: str, redirect_uri: str) -> SsoProfile: ...
```

`SsoProfile`: `provider`, `subject`, `email`, `name`, `avatar_url`.

Config via env or `config.yaml` section `auth.sso.providers` (client_id, client_secret, issuer).

## Step 2: HTTP routes

Prefix `/api/auth/sso`:

| Route | Behavior |
| --- | --- |
| `GET /providers` | Public list of enabled providers + display names |
| `GET /{provider}/start` | Set CSRF state cookie; redirect to IdP |
| `GET /callback` | Exchange code; find or create user; issue session |
| `POST /link` | Authenticated user links provider (same email verification optional) |
| `DELETE /link/{provider}` | Unlink (require password or step-up from 217) |

**User provisioning rules:**

- If email matches existing user: link identity (with confirmation if logged in).
- If new: create user with random password, `is_approved` per instance policy, role `user`.
- Audit: `sso_login`, `sso_link`, `sso_unlink`.

Return same shape as password login: `{ token, user }` + set cookie if middleware expects it.

## Step 3: Frontend login

Update `LoginForm.tsx` / `AuthLayout.tsx`:

- Fetch `GET /api/auth/sso/providers` on mount.
- Render provider buttons above credential form ("Continue with Google", etc.).
- Buttons navigate to `/api/auth/sso/{provider}/start?return_to=...`

Create `/auth/sso/callback/page.tsx` (or handle server redirect):

- If token in query fragment/cookie, call `setCESession` and redirect to `return_to`.

## Step 4: Connected accounts page

`/settings/account/connected-accounts/page.tsx`:

- List linked providers with unlink button.
- "Link Google" etc. for signed-in user.
- Show warning if SSO is only login method and unlink would lock account (require password set first).

## Step 5: Tests

- `tests/auth/test_sso_callback.py`: mock IdP token exchange; user create vs link.
- `tests/auth/test_sso_link.py`: link/unlink rules.
- Provider registry loads only configured providers.

## Acceptance criteria

| # | Test |
| --- | --- |
| 1 | `GET /api/auth/sso/providers` lists enabled providers |
| 2 | Callback creates session for new SSO user |
| 3 | Matching email links to existing account when policy allows |
| 4 | Logged-in user links and unlinks provider |
| 5 | Login page shows SSO buttons when configured |
| 6 | No secrets in frontend bundle |
| 7 | `pytest tests/auth/test_sso_callback.py` passes |

## Dependencies

- Prompt 214 (profile email for matching).
- Prompt 215 or 217 (password/step-up before unlink).

## Notes

- LDAP/SAML deferred; OIDC generic covers many IdPs.
- Reuse httpx for token exchange; no heavy SDK required for Google/GitHub.

## Archive

`prompts-archive/` when AC pass.
