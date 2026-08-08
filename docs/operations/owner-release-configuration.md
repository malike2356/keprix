# Owner release configuration

All code and workflows can be prepared without publishing credentials. The owner
must complete these settings before the first public stable release.

## GitHub protected environments

Create environments named `pypi`, `dockerhub`, `desktop-macos`, and
`desktop-windows`. Require owner approval for each production deployment.

| Environment | Configuration |
| --- | --- |
| `pypi` | Add this repository as a PyPI trusted publisher. No API token is required. |
| `dockerhub` | `DOCKERHUB_USERNAME`, `DOCKERHUB_TOKEN` with repository-scoped write access. |
| `desktop-macos` | `APPLE_ID`, `APPLE_TEAM_ID`, `APPLE_APP_SPECIFIC_PASSWORD`, and Apple signing certificate. |
| `desktop-windows` | `WIN_CSC_LINK`, `WIN_CSC_KEY_PASSWORD`, backed by the selected code-signing provider. |

Runtime model, email, channel, CRM, and sidecar credentials remain configurable
through Keprix encrypted credential settings. Release credentials are intentionally
excluded from that GUI because repository publishing is outside a tenant runtime.

Run `bash scripts/check-release-configuration.sh` in a secure CI environment to
list missing configuration. The script reports names only and never prints values.
