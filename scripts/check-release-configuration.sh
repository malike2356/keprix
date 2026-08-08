#!/usr/bin/env bash
set -euo pipefail

missing=0
check() {
  local name="$1"
  local purpose="$2"
  if [[ -n "${!name:-}" ]]; then
    printf 'READY   %s: %s\n' "$name" "$purpose"
  else
    printf 'CONFIG  %s: %s\n' "$name" "$purpose"
    missing=1
  fi
}

echo "Keprix release configuration readiness"
check DOCKERHUB_USERNAME "Docker Hub publisher account"
check DOCKERHUB_TOKEN "Docker Hub scoped access token"
check APPLE_ID "Apple notarization account"
check APPLE_TEAM_ID "Apple developer team"
check APPLE_APP_SPECIFIC_PASSWORD "Apple notarization password"
check WIN_CSC_LINK "Windows signing certificate secret or URL"
check WIN_CSC_KEY_PASSWORD "Windows signing certificate password"

echo
echo "PyPI uses GitHub Actions OIDC and should not use a long-lived API token."
echo "Configure all values as GitHub Environment secrets, never in .env or the Keprix database."
exit "$missing"
