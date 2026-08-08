#!/usr/bin/env bash
# Thin alias for the README one-liner. Pipes the same raw GitHub install.sh.
# This development-channel helper follows main. Stable releases use
# scripts/install-release.sh with an immutable manifest and signature checks.
set -euo pipefail
curl -fsSL https://raw.githubusercontent.com/malike2356/keprix/main/scripts/install.sh | bash
