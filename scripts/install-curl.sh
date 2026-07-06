#!/usr/bin/env bash
# One-liner entrypoint served from GitHub raw.
set -euo pipefail
curl -fsSL https://raw.githubusercontent.com/malike2356/keprix/main/scripts/install.sh | bash
