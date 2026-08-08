#!/usr/bin/env bash
# Install an immutable, verified Keprix release without root access.
set -euo pipefail

REPOSITORY="${KEPRIX_REPOSITORY:-malike2356/keprix}"
CHANNEL="${KEPRIX_RELEASE_CHANNEL:-stable}"
VERSION="${KEPRIX_VERSION:-}"
PREFIX="${KEPRIX_PREFIX:-$HOME/.local/share/keprix}"
BIN_DIR="${KEPRIX_BIN_DIR:-$HOME/.local/bin}"
NON_INTERACTIVE=0
DRY_RUN=0
DOCTOR=0
UNINSTALL=0
REPAIR=0
KEEP_DATA=1
PYTHON="${PYTHON:-python3}"

usage() {
  cat <<'EOF'
Usage: install-release.sh [options]
  --channel stable|beta     Release channel (default: stable)
  --version X.Y.Z           Install an exact version
  --prefix PATH             Program installation root
  --bin-dir PATH            Command link directory
  --non-interactive         Do not prompt
  --dry-run                 Print the plan without changing the system
  --doctor                  Check compatibility without installing
  --repair                  Reinstall the selected version, preserving data
  --uninstall               Remove program files and command link
  --delete-data             With --uninstall, also remove Keprix user data
  -h, --help                Show help
EOF
}

die() { echo "ERROR: $*" >&2; exit 1; }
note() { echo "==> $*"; }

while [[ $# -gt 0 ]]; do
  case "$1" in
    --channel) CHANNEL="${2:-}"; shift 2 ;;
    --version) VERSION="${2:-}"; shift 2 ;;
    --prefix) PREFIX="${2:-}"; shift 2 ;;
    --bin-dir) BIN_DIR="${2:-}"; shift 2 ;;
    --non-interactive) NON_INTERACTIVE=1; shift ;;
    --dry-run) DRY_RUN=1; shift ;;
    --doctor) DOCTOR=1; shift ;;
    --repair) REPAIR=1; shift ;;
    --uninstall) UNINSTALL=1; shift ;;
    --delete-data) KEEP_DATA=0; shift ;;
    -h|--help) usage; exit 0 ;;
    *) die "Unknown option: $1" ;;
  esac
done

[[ "$CHANNEL" == stable || "$CHANNEL" == beta ]] || die "Channel must be stable or beta"
[[ "$PREFIX" = /* ]] || die "--prefix must be an absolute path"
[[ "$BIN_DIR" = /* ]] || die "--bin-dir must be an absolute path"
[[ "$PREFIX" != / && "$PREFIX" != "$HOME" ]] || die "Refusing broad installation prefix"

user_data="${KEPRIX_HOME:-$HOME/.keprix}"
venv="$PREFIX/venv"
command_path="$BIN_DIR/keprix"
state_file="$PREFIX/install-state.json"

run_doctor() {
  local failed=0 os arch free_kb
  os="$(uname -s 2>/dev/null || true)"
  arch="$(uname -m 2>/dev/null || true)"
  case "$os" in Linux|Darwin) ;; *) echo "FAIL: unsupported OS $os"; failed=1 ;; esac
  case "$arch" in x86_64|amd64|arm64|aarch64) ;; *) echo "FAIL: unsupported architecture $arch"; failed=1 ;; esac
  if ! command -v "$PYTHON" >/dev/null 2>&1; then
    echo "FAIL: python3 is missing"; failed=1
  elif ! "$PYTHON" -c 'import sys; raise SystemExit(0 if (3, 11) <= sys.version_info[:2] < (3, 13) else 1)'; then
    echo "FAIL: Keprix requires Python 3.11 or 3.12"; failed=1
  else
    echo "PASS: $($PYTHON --version 2>&1)"
  fi
  for tool in curl; do
    if command -v "$tool" >/dev/null 2>&1; then echo "PASS: $tool found"; else echo "FAIL: $tool missing"; failed=1; fi
  done
  if command -v sha256sum >/dev/null 2>&1 || command -v shasum >/dev/null 2>&1; then
    echo "PASS: SHA-256 tool found"
  else
    echo "FAIL: sha256sum or shasum is required"; failed=1
  fi
  free_kb="$(df -Pk "$(dirname "$PREFIX")" 2>/dev/null | awk 'NR==2 {print $4}' || true)"
  if [[ "$free_kb" =~ ^[0-9]+$ && "$free_kb" -lt 5242880 ]]; then
    echo "FAIL: less than 5 GB free near $PREFIX"; failed=1
  else
    echo "PASS: installation storage check"
  fi
  [[ -w "$(dirname "$PREFIX")" || ! -e "$(dirname "$PREFIX")" ]] || {
    echo "FAIL: parent of $PREFIX is not writable"; failed=1;
  }
  return "$failed"
}

if [[ "$DOCTOR" == 1 ]]; then run_doctor; exit $?; fi

if [[ "$UNINSTALL" == 1 ]]; then
  note "Uninstall plan: remove $PREFIX and $command_path"
  [[ "$KEEP_DATA" == 1 ]] && note "User data will be preserved at $user_data" || note "User data will be removed: $user_data"
  [[ "$DRY_RUN" == 1 ]] && exit 0
  [[ -L "$command_path" ]] && rm "$command_path"
  [[ -d "$PREFIX" ]] && rm -rf -- "$PREFIX"
  if [[ "$KEEP_DATA" == 0 ]]; then
    [[ "$user_data" != / && "$user_data" != "$HOME" ]] || die "Refusing broad user-data path"
    if [[ "$NON_INTERACTIVE" != 1 ]]; then
      read -r -p "Permanently delete $user_data? Type DELETE: " answer
      [[ "$answer" == DELETE ]] || die "Data deletion cancelled"
    fi
    [[ -d "$user_data" ]] && rm -rf -- "$user_data"
  fi
  note "Keprix program uninstall complete"
  exit 0
fi

run_doctor || die "Compatibility checks failed"

resolve_version() {
  if [[ -n "$VERSION" ]]; then printf '%s\n' "${VERSION#v}"; return; fi
  local api="https://api.github.com/repos/$REPOSITORY/releases"
  [[ "$CHANNEL" == stable ]] && api="$api/latest"
  curl -fsSL --proto '=https' --tlsv1.2 "$api" | "$PYTHON" -c '
import json, sys
data=json.load(sys.stdin)
if isinstance(data, list):
    data=next((r for r in data if r.get("prerelease") and not r.get("draft")), {})
tag=str(data.get("tag_name") or "").removeprefix("v")
if not tag: raise SystemExit("No eligible public release found")
print(tag)'
}

VERSION="$(resolve_version)"
[[ "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+([.-][0-9A-Za-z.-]+)?$ ]] || die "Invalid release version: $VERSION"
tag="v$VERSION"
base_url="https://github.com/$REPOSITORY/releases/download/$tag"
manifest_url="$base_url/release-manifest.json"

note "Install Keprix $VERSION from immutable tag $tag"
note "Prefix: $PREFIX"
note "Manifest: $manifest_url"
if [[ "$DRY_RUN" == 1 ]]; then exit 0; fi

tmp_dir="$(mktemp -d)"
trap 'rm -rf -- "$tmp_dir"' EXIT
manifest="$tmp_dir/release-manifest.json"
curl -fsSL --proto '=https' --tlsv1.2 "$manifest_url" -o "$manifest"

readarray -t artifact < <("$PYTHON" - "$manifest" "$VERSION" <<'PY'
import json, sys
data=json.load(open(sys.argv[1], encoding="utf-8"))
if data.get("schema") != "keprix.release-manifest.v1": raise SystemExit("Unsupported manifest schema")
if data.get("version") != sys.argv[2]: raise SystemExit("Manifest version mismatch")
rows=[a for a in data.get("artifacts", []) if a.get("kind") == "wheel"]
if len(rows) != 1: raise SystemExit("Release must contain exactly one universal wheel")
row=rows[0]
for key in ("url", "sha256", "signature_url"):
    print(row.get(key, ""))
PY
)
artifact_url="${artifact[0]:-}"
expected_sha="${artifact[1]:-}"
signature_url="${artifact[2]:-}"
[[ "$artifact_url" == "$base_url/"* ]] || die "Manifest wheel URL is not under the immutable release"
[[ "$expected_sha" =~ ^[0-9a-f]{64}$ ]] || die "Manifest SHA-256 is invalid"

wheel="$tmp_dir/${artifact_url##*/}"
curl -fsSL --proto '=https' --tlsv1.2 "$artifact_url" -o "$wheel"
if command -v sha256sum >/dev/null 2>&1; then
  printf '%s  %s\n' "$expected_sha" "$wheel" | sha256sum -c -
else
  actual_sha="$(shasum -a 256 "$wheel" | awk '{print $1}')"
  [[ "$actual_sha" == "$expected_sha" ]] || die "Wheel SHA-256 mismatch"
fi

if command -v cosign >/dev/null 2>&1; then
  signature="$tmp_dir/${signature_url##*/}"
  curl -fsSL --proto '=https' --tlsv1.2 "$signature_url" -o "$signature"
  cosign verify-blob --bundle "$signature" \
    --certificate-identity-regexp "https://github.com/$REPOSITORY/.*" \
    --certificate-oidc-issuer https://token.actions.githubusercontent.com "$wheel"
elif [[ "$CHANNEL" == stable ]]; then
  die "cosign is required to verify stable releases"
else
  note "WARNING: cosign is missing; beta signature verification was skipped"
fi

if [[ -e "$PREFIX" && "$REPAIR" != 1 ]]; then
  die "$PREFIX already exists; use --repair or choose another prefix"
fi
mkdir -p "$PREFIX" "$BIN_DIR"
"$PYTHON" -m venv "$venv"
"$venv/bin/python" -m pip install --disable-pip-version-check "$wheel"
"$venv/bin/python" -m pip check
ln -sfn "$venv/bin/keprix" "$command_path"
"$PYTHON" - "$state_file" "$VERSION" "$tag" "$expected_sha" <<'PY'
import json, pathlib, sys
path=pathlib.Path(sys.argv[1])
path.write_text(json.dumps({"version":sys.argv[2],"tag":sys.argv[3],"sha256":sys.argv[4]}, indent=2)+"\n")
PY
note "Installed Keprix $VERSION. Run: $command_path setup"
