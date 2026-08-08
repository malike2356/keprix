# Security Policy

## Supported versions

Only the latest release receives security updates. Older tags are unsupported.

| Version | Supported |
| --- | --- |
| latest release | yes |
| older tags | no |

## Reporting a vulnerability

Do not open a public GitHub issue for security vulnerabilities.

Report privately to **security@carinaai.uk**.

We aim to:

- acknowledge reports within **48 hours**
- provide an initial remediation timeline within **7 days**
- follow a **90-day coordinated disclosure** window unless a fix ships sooner

Include in your report:

- a concise description of the issue
- steps to reproduce on `main` or the latest release
- impact assessment (confidentiality, integrity, availability)
- affected component paths if known
- a suggested fix if you have one

## What not to do

- Do not disclose the vulnerability publicly before coordinated release.
- Do not include live credentials, customer data, or production secrets in reports.

## Bug bounty

There is no paid bug bounty at this time. Security researchers are credited in
`CHANGELOG.md` and `THIRD_PARTY_NOTICES.md` unless anonymity is requested.

## Related policies

- Contributor expectations: [docs/community/code-of-conduct.md](docs/community/code-of-conduct.md)
- Contribution workflow: [CONTRIBUTING.md](CONTRIBUTING.md)

## Universal Sidecar

Security issues in the Universal Sidecar (`/sidecar/v1`, manifests,
connectors, pairing) must use the private disclosure process above.
See also [docs/universal-sidecar/security-policy.md](docs/universal-sidecar/security-policy.md).
