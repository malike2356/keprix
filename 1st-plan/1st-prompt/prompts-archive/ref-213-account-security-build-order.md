# Account and security: build order and prompt map

Reference for prompts **214-219**. Architecture reference:
`prompts-archive/ref-213-account-security-architecture-reference.md`.

## Build order

```
214 Account profile API + UI
  |
215 Password change + forgot reset
  |
216 TOTP UI + recovery codes + login 2FA step
  |
217 Email OTP step-up
  |
218 SSO/OAuth workspace login
  |
219 Security hub + sessions + nav polish
```

| Order | Prompt | Title | Est. focus |
| --- | --- | --- | --- |
| 1 | 214 | Account profile | Backend PATCH + profile page |
| 2 | 215 | Password reset | Token store + forgot/reset pages |
| 3 | 216 | 2FA TOTP UI | QR enroll, recovery codes, login step |
| 4 | 217 | Email OTP | Challenge store + login fallback |
| 5 | 218 | SSO/OAuth | Provider registry + callback |
| 6 | 219 | Security hub | Sessions, settings card, avatar links |

## Parallel work (optional)

| Pair | Note |
| --- | --- |
| 214 + 219 shell | 219 can ship a stub hub first; 214 fills profile tab |
| 217 + 218 | Independent after 215 rate-limit patterns exist |

## Deferred (no prompt in this series)

| Item | Reason |
| --- | --- |
| LDAP/SAML | Enterprise tier |
| WebAuthn passkeys | Follow-on prompt 220+ |
| SMS OTP (Twilio) | Email OTP sufficient for v1 |
| Avatar file upload to S3 | URL field v1; upload later |

## License boundary

Reuse patterns from `keprix_cli/dashboard_auth/` for SSO; do not copy proprietary IdP SDKs
into `src/keprix/` without compatible licenses.
