#!/usr/bin/env bash
# Thin alias for the README one-liner. Fetches the same public installer.
# This development-channel helper follows main. Stable releases use
# scripts/install-release.sh with an immutable manifest and signature checks.
set -euo pipefail
curl -fsSL https://keprixai.com/install.sh | bash
