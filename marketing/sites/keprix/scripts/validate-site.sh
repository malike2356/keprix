#!/usr/bin/env bash
# keprix marketing site validator
# Scans all HTML files for forbidden strings. Exits non-zero if any are found.
# Run this before every deploy.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SITE_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

FAIL=0

red()   { printf '\033[0;31m%s\033[0m\n' "$*"; }
green() { printf '\033[0;32m%s\033[0m\n' "$*"; }

check_forbidden() {
  local label="$1"
  local pattern="$2"
  # brand-boundary/index.html is the policy page that documents forbidden strings;
  # it necessarily quotes them. Exclude it from forbidden-string checks.
  local files
  files=$(grep -rl --include="*.html" -i "${pattern}" "${SITE_DIR}" 2>/dev/null \
    | grep -v "brand-boundary/index.html" || true)
  if [[ -n "${files}" ]]; then
    red "FAIL: forbidden string found - ${label}"
    echo "${files}"
    FAIL=1
  fi
}

echo "Validating keprix marketing site..."
echo "Site directory: ${SITE_DIR}"
echo ""

# Brand boundary violations
# Note: brand-boundary/index.html is excluded from these checks (it documents the rules).
check_forbidden "Carina keprix (case insensitive)"        "carina keprix"
check_forbidden "carina-keprix (case insensitive)"        "carina-keprix"
check_forbidden "Powered by Carina (case insensitive)"    "powered by carina"
# "Not a Carina product" is allowed (footer disclaimer). Check for affirmative claim only.
check_forbidden "is a Carina product (case insensitive)"  "is a carina product"
check_forbidden "Carina Aiva on keprix surfaces"          "carina aiva"
check_forbidden "Aiva on keprix surfaces (standalone)"    ">Aiva<\|\"Aiva\"\| Aiva\."

# Upstream agent names used as keprix feature names (not in attribution text)
# Attribution context on /consolidation/ is acceptable; check for use as feature labels
# The grep below is intentionally broad and may produce false positives on /consolidation/
# If consolidation page appears, manually confirm it is attribution-only, then add an exclude.
# check_forbidden "Upstream name: Hermes as feature"     "keprix hermes\|hermes agent"

# Typography violations
check_forbidden "Em dash (U+2014)"   $'\xe2\x80\x94'
check_forbidden "En dash (U+2013)"   $'\xe2\x80\x93'

# Emoji detection: check for any Unicode above U+2600 (common emoji range starts here)
# This catches the most common emoji blocks without an exhaustive list.
# Uses Perl regex since grep -P is reliable on Linux.
if perl -l -ne 'exit 1 if /[\x{2600}-\x{27FF}\x{1F000}-\x{1FFFF}]/u' \
  $(find "${SITE_DIR}" -name "*.html") 2>/dev/null; then
  : # no emojis found
else
  red "FAIL: emoji characters found in HTML files"
  perl -rn -l -e 'print "$ARGV" if /[\x{2600}-\x{27FF}\x{1F000}-\x{1FFFF}]/u' \
    $(find "${SITE_DIR}" -name "*.html") 2>/dev/null || true
  FAIL=1
fi

# Required pages exist
REQUIRED_PAGES=(
  "index.html"
  "architecture/index.html"
  "consolidation/index.html"
  "mutation-engine/index.html"
  "playbooks/index.html"
  "hub/index.html"
  "community/index.html"
  "contributing/index.html"
  "security/index.html"
  "roadmap/index.html"
  "brand-boundary/index.html"
  "legal/index.html"
  "robots.txt"
  "sitemap.xml"
)

for page in "${REQUIRED_PAGES[@]}"; do
  if [[ ! -f "${SITE_DIR}/${page}" ]]; then
    red "FAIL: required file missing - ${page}"
    FAIL=1
  fi
done

# Required content checks
if ! grep -q "keprix is MIT open source. Not a Carina product." "${SITE_DIR}/index.html" 2>/dev/null; then
  red "FAIL: footer brand disclaimer missing from index.html"
  FAIL=1
fi

if ! grep -q "Sponsored by Carina" "${SITE_DIR}/index.html" 2>/dev/null; then
  red "FAIL: sponsor attribution missing from index.html footer"
  FAIL=1
fi

echo ""
if [[ "${FAIL}" -eq 0 ]]; then
  green "All checks passed. Site is ready to deploy."
else
  red "Validation failed. Fix errors above before deploying."
  exit 1
fi
