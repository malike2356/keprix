#!/usr/bin/env bash
# Thin alias for the README one-liner. Pipes the same raw GitHub install.sh.
# Note: this URL 404s until the GitHub repo is anonymously public
# (see docs/operations/public-github-checklist.md). Fail-closed is intentional.
set -euo pipefail
curl -fsSL https://raw.githubusercontent.com/malike2356/keprix/main/scripts/install.sh | bash
