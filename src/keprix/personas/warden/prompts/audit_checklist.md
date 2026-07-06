# WARDEN Security Audit Checklist

## Configuration

- [ ] Security headers enabled (CSP, X-Frame-Options, HSTS when HTTPS)
- [ ] Debug mode disabled in production
- [ ] Default credentials removed
- [ ] File permissions restrict sensitive config files

## Secrets and Credentials

- [ ] No API keys or tokens in source code or logs
- [ ] Environment variables used for secrets (not committed)
- [ ] Vault or credential store in use where applicable
- [ ] Connection strings do not embed plaintext passwords

## Dependencies

- [ ] Dependencies pinned to known-good versions
- [ ] No critical or high CVEs in direct dependencies
- [ ] Lockfiles committed and up to date

## Access Control

- [ ] API keys rotated on schedule
- [ ] Least-privilege permissions for service accounts
- [ ] Human approval required for destructive operations

## Application Security

- [ ] Input validation at API boundaries
- [ ] Prompt injection heuristics enabled for agent inputs
- [ ] Rate limiting configured for public endpoints

## Severity Guide

| Severity | Criteria | Response time |
|----------|----------|---------------|
| Critical | Active secret exposure, RCE risk, auth bypass | Immediate |
| High | Missing hardening on public surface, high CVE | Same day |
| Medium | Unpinned deps, weak config, missing headers | This sprint |
| Low | Informational, defense-in-depth improvements | Backlog |
